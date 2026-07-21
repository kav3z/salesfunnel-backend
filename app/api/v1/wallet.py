# internal imports
from app.core.config import settings
from app.core.helpers import audit_action
from app.core.dependencies import CurrentUser, DBSession
from app.models.wallet import Wallet
from app.models.wallet_transaction import (
    WalletTransaction, TransactionType, TransactionPurpose, TransactionStatus
)
from app.models.distributor_profile import DistributorProfile
from app.models.wholesaler_profile import WholesalerProfile
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus

# external imports
import json
import httpx
import uuid
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timedelta
import pytz
from sqlmodel import select
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, status, Query

v1_wallet = APIRouter(prefix="/v1/wallet", tags=["v1_wallet"])
db_dependency = DBSession

# Request/Response Schemas
class ResolveBankResponse(BaseModel):
    status: bool
    message: str
    data: dict

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": True,
                "message": "Account number resolved successfully",
                "data": {
                    "account_number": "0123456789",
                    "account_name": "JOHN DOE",
                    "bank_id": 9
                }
            }
        }
    )

class UpdateBankRequest(BaseModel):
    account_name: str = Field(..., description="Account holder name")
    account_number: str = Field(..., description="10-digit NUBAN account number")
    bank_name: str = Field(..., description="Name of the bank")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_name": "JOHN DOE",
                "account_number": "0123456789",
                "bank_name": "Access Bank"
            }
        }
    )

class AssignDedicatedAccountRequest(BaseModel):
    preferred_bank: str = Field("wema-bank", description="Preferred bank slug (e.g. wema-bank, test-bank)")
    first_name: Optional[str] = Field(None, description="Optional override first name")
    middle_name: Optional[str] = Field(None, description="Optional override middle name")
    last_name: Optional[str] = Field(None, description="Optional override last name")
    phone: Optional[str] = Field(None, description="Optional override phone number")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "preferred_bank": "wema-bank",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+2348012345678"
            }
        }
    )

class WalletBalanceResponse(BaseModel):
    total_balance: Decimal
    withdrawable_balance: Decimal | None = None
    locked_balance: Decimal | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_balance": "250000.00",
                "withdrawable_balance": "200000.00",
                "locked_balance": "50000.00"
            }
        }
    )

class WalletTransactionResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    amount: Decimal
    type: TransactionType
    purpose: TransactionPurpose
    status: TransactionStatus
    reference: str
    description: Optional[str]
    created_at: datetime
    available_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "e81d71c9-e9e4-49d8-96be-8248f20d5a11",
                "wallet_id": "b11d71c9-e9e4-49d8-96be-8248f20d5a77",
                "amount": "50000.00",
                "type": "credit",
                "purpose": "funding",
                "status": "completed",
                "reference": "FUND-REF-100293",
                "description": "Wallet funding charge",
                "created_at": "2026-07-19T10:00:00Z",
                "available_at": "2026-07-19T10:00:00Z"
            }
        }
    )

class FundWalletRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount to fund in Naira")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "50000.00"
            }
        }
    )

class FundWalletResponse(BaseModel):
    status: str
    message: str
    authorization_url: str
    reference: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Authorization URL created",
                "authorization_url": "https://checkout.paystack.com/001122334455",
                "reference": "FUND-REF-100293"
            }
        }
    )

class PayOrderRequest(BaseModel):
    order_id: uuid.UUID = Field(..., description="UUID of the unpaid order to pay for")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_id": "a11d71c9-e9e4-49d8-96be-8248f20d5a22"
            }
        }
    )

class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount to withdraw in Naira")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "25000.00"
            }
        }
    )

# Helpers
def get_or_create_wallet(db: db_dependency, user_id: uuid.UUID) -> Wallet:
    statement = select(Wallet).where(Wallet.user_id == user_id)
    wallet = db.exec(statement).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet

async def get_bank_code_by_name(bank_name: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            response = await client.get("https://api.paystack.co/bank", headers=headers)
            if response.status_code == 200:
                banks = response.json().get("data", [])
                for b in banks:
                    if b["name"].lower() == bank_name.lower():
                        return b["code"]
    except Exception as e:
        print(f"Error fetching bank code: {e}")
    return None

# Endpoints

@v1_wallet.get(
    "/bank/resolve", 
    response_model=ResolveBankResponse,
    summary="Resolve NUBAN Bank Account",
    description="Validate NUBAN bank account number and fetch corresponding account holder name using Paystack API."
)
async def resolve_bank_account(
    current_user: CurrentUser,
    account_number: str = Query(..., min_length=10, max_length=10, description="10-digit NUBAN account number", examples=["0123456789"]),
    bank_code: str = Query(..., description="Paystack bank code", examples=["044"])
):
    """Resolve bank account details using Paystack API"""
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Paystack secret key not configured")
    
    url = f"https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        
        data = response.json()
        if response.status_code == 200 and data.get("status") is True:
            return ResolveBankResponse(
                status=True,
                message=data.get("message", "Account resolved"),
                data=data.get("data", {})
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Could not resolve account")
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Paystack: {str(e)}")


@v1_wallet.post(
    "/bank/update",
    summary="Update Settlement Bank Details",
    description="Update settlement bank account details for distributor payout and activate bank status."
)
async def update_distributor_bank_details(
    request_data: UpdateBankRequest,
    current_user: CurrentUser,
    db: db_dependency,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Update distributor bank details in profile and set is_bank_active to True"""
    if current_user.role != UserRole.DISTRIBUTOR:
        raise HTTPException(
            status_code=400,
            detail="Only distributors can update settlement bank details"
        )
    
    statement = select(DistributorProfile).where(DistributorProfile.user_id == current_user.id)
    profile = db.exec(statement).first()
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Distributor profile not found. Please create a profile first."
        )
    
    old_value = {
        "bank_name": profile.bank_name,
        "account_name": profile.account_name,
        "account_number": profile.account_number,
        "is_bank_active": profile.is_bank_active
    }

    profile.bank_name = request_data.bank_name
    profile.account_name = request_data.account_name
    profile.account_number = request_data.account_number
    profile.is_bank_active = True
    
    db.add(profile)
    db.commit()
    db.refresh(profile)

    background_tasks.add_task(
        audit_action,
        user_id=current_user.id,
        user_email=current_user.email,
        action_type="UPDATE",
        entity_type="DistributorProfile",
        entity_id=str(profile.id),
        old_value=old_value,
        new_value={
            "bank_name": profile.bank_name,
            "account_name": profile.account_name,
            "account_number": profile.account_number,
            "is_bank_active": profile.is_bank_active
        },
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")
    )

    return {"status": "success", "message": "Settlement bank details updated and activated successfully"}


@v1_wallet.post(
    "/dedicated-account/assign",
    summary="Assign Dedicated Virtual Account",
    description="Assign a Paystack dedicated virtual bank account to a wholesaler account."
)
async def assign_dedicated_account(
    request_data: AssignDedicatedAccountRequest,
    current_user: CurrentUser,
    db: db_dependency,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Assign a Paystack Dedicated (Virtual) Account to the logged-in user profile"""
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Paystack secret key not configured")

    # Retrieve corresponding profile (only wholesalers can create virtual accounts)
    if current_user.role != UserRole.WHOLESALER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only wholesalers can create dedicated virtual accounts"
        )

    profile = db.exec(select(WholesalerProfile).where(WholesalerProfile.user_id == current_user.id)).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create your profile first.")

    # Parse first, middle, last name from user's full name if not overridden
    names = current_user.full_name.split()
    first_name = request_data.first_name or (names[0] if len(names) > 0 else "First")
    last_name = request_data.last_name or (names[-1] if len(names) > 1 else "Last")
    middle_name = request_data.middle_name or (" ".join(names[1:-1]) if len(names) > 2 else "")
    phone = request_data.phone or current_user.phone

    payload = {
        "email": current_user.email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "preferred_bank": request_data.preferred_bank,
        "country": "NG"
    }
    if middle_name:
        payload["middle_name"] = middle_name

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.paystack.co/dedicated_account/assign",
                json=payload,
                headers=headers,
                timeout=15.0
            )
        
        data = response.json()
        if response.status_code == 200 and data.get("status") is True:
            # Dedicated account assigned or creation in progress
            dedicated_account_id = data.get("data", {}).get("id")
            if not dedicated_account_id:
                # Paystack sometimes returns it under dedicated_account_id or assignment details
                dedicated_account_id = data.get("data", {}).get("dedicated_account_id")
            
            if dedicated_account_id:
                profile.paystack_dedicated_account_id = str(dedicated_account_id)
                db.add(profile)
                db.commit()

            return data
        else:
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Paystack dedicated account assignment failed")
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Paystack: {str(e)}")


@v1_wallet.get(
    "/dedicated-account",
    summary="Get Dedicated Virtual Account Details",
    description="Retrieve bank name, account number, and account name for the wholesaler's dedicated virtual account."
)
async def get_dedicated_account_details(
    current_user: CurrentUser,
    db: db_dependency
):
    """Retrieve details of the Paystack Dedicated (Virtual) Account assigned to the user profile"""
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Paystack secret key not configured")

    if current_user.role != UserRole.WHOLESALER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only wholesalers have dedicated virtual accounts"
        )

    profile = db.exec(select(WholesalerProfile).where(WholesalerProfile.user_id == current_user.id)).first()
    
    if not profile or not profile.paystack_dedicated_account_id:
        raise HTTPException(
            status_code=404,
            detail="No dedicated virtual account has been assigned to your profile yet"
        )
    
    account_id = profile.paystack_dedicated_account_id
    url = f"https://api.paystack.co/dedicated_account/{account_id}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        
        data = response.json()
        if response.status_code == 200 and data.get("status") is True:
            account_info = data.get("data", {})
            return {
                "account_name": account_info.get("account_name"),
                "account_number": account_info.get("account_number"),
                "bank_name": account_info.get("bank", {}).get("name")
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Failed to retrieve dedicated account details from Paystack")
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Paystack: {str(e)}")


@v1_wallet.get(
    "/balance", 
    response_model=WalletBalanceResponse,
    summary="Get Wallet Balance",
    description="Retrieve wallet total balance, withdrawable balance, and locked balance breakdown."
)
async def get_wallet_balance(
    current_user: CurrentUser,
    db: db_dependency
):
    """Get the wallet balances (dynamic balance calculation, locked balance, withdrawable balance)"""
    wallet = get_or_create_wallet(db, current_user.id)
    total_balance = wallet.balance

    if current_user.role == UserRole.WHOLESALER:
        # Wholesalers do not have a payout lock
        return WalletBalanceResponse(
            total_balance=total_balance
        )
    
    # For distributors, calculate withdrawable balance dynamically based on available credits minus debits
    now = datetime.utcnow()
    
    # 1. Sum of COMPLETED credits that are currently available (available_at <= now)
    credits_stmt = select(WalletTransaction).where(
        WalletTransaction.wallet_id == wallet.id,
        WalletTransaction.type == TransactionType.CREDIT,
        WalletTransaction.status == TransactionStatus.COMPLETED,
        WalletTransaction.available_at <= now
    )
    credits_sum = sum(tx.amount for tx in db.exec(credits_stmt).all())

    # 2. Sum of all DEBITS (COMPLETED or PENDING)
    debits_stmt = select(WalletTransaction).where(
        WalletTransaction.wallet_id == wallet.id,
        WalletTransaction.type == TransactionType.DEBIT,
        WalletTransaction.status.in_([TransactionStatus.COMPLETED, TransactionStatus.PENDING])
    )
    debits_sum = sum(tx.amount for tx in db.exec(debits_stmt).all())

    # Withdrawable balance cannot be negative or exceed total balance
    withdrawable_balance = max(Decimal("0.00"), credits_sum - debits_sum)
    withdrawable_balance = min(withdrawable_balance, total_balance)

    locked_balance = max(Decimal("0.00"), total_balance - withdrawable_balance)

    return WalletBalanceResponse(
        total_balance=total_balance,
        withdrawable_balance=withdrawable_balance,
        locked_balance=locked_balance
    )


@v1_wallet.get(
    "/history", 
    response_model=List[WalletTransactionResponse],
    summary="Get Wallet Transaction History",
    description="Retrieve chronological transaction history (credits, debits, funding, withdrawals) for the user's wallet."
)
async def get_wallet_history(
    current_user: CurrentUser,
    db: db_dependency
):
    """Retrieve transaction history for the user's wallet"""
    wallet = get_or_create_wallet(db, current_user.id)
    statement = select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id).order_by(WalletTransaction.created_at.desc())
    transactions = db.exec(statement).all()
    return transactions


@v1_wallet.post(
    "/fund/initialize", 
    response_model=FundWalletResponse,
    summary="Initialize Wallet Funding",
    description="Initialize a Paystack checkout transaction to fund the wholesaler's wallet."
)
async def initialize_wallet_funding(
    request_data: FundWalletRequest,
    current_user: CurrentUser,
    db: db_dependency,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Initialize a Paystack payment checkout to fund the wholesaler's wallet"""
    if current_user.role != UserRole.WHOLESALER:
        raise HTTPException(
            status_code=403,
            detail="Only wholesalers can fund wallets directly"
        )
    
    wallet = get_or_create_wallet(db, current_user.id)
    
    # Generate unique reference
    reference = f"wfund_{uuid.uuid4().hex[:12]}_{int(datetime.utcnow().timestamp())}"
    
    # Create PENDING transaction in ledger
    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=request_data.amount,
        type=TransactionType.CREDIT,
        purpose=TransactionPurpose.FUNDING,
        status=TransactionStatus.PENDING,
        reference=reference,
        description=f"Fund wallet request of ₦{request_data.amount}",
        available_at=datetime.utcnow()
    )
    db.add(tx)
    db.commit()

    # Prepare Paystack request
    payload = {
        "email": current_user.email,
        "amount": int(request_data.amount * 100), # to kobo
        "reference": reference,
        "metadata": {
            "type": "wallet_funding",
            "wholesaler_id": str(current_user.id),
            "wallet_id": str(wallet.id)
        }
    }
    
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=15.0
            )
        
        data = response.json()
        if response.status_code == 200 and data.get("status") is True:
            background_tasks.add_task(
                audit_action,
                user_id=current_user.id,
                user_email=current_user.email,
                action_type="INITIALIZE_FUNDING",
                entity_type="WalletTransaction",
                entity_id=str(tx.id),
                old_value=None,
                new_value={
                    "amount": str(request_data.amount),
                    "reference": reference
                },
                ip_address=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", "")
            )
            return FundWalletResponse(
                status="success",
                message="Wallet funding checkout initialized",
                authorization_url=data["data"]["authorization_url"],
                reference=reference
            )
        else:
            tx.status = TransactionStatus.FAILED
            db.add(tx)
            db.commit()
            raise HTTPException(status_code=400, detail=data.get("message", "Paystack initialization failed"))
            
    except httpx.RequestError as e:
        tx.status = TransactionStatus.FAILED
        db.add(tx)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to connect to Paystack: {str(e)}")


@v1_wallet.post(
    "/pay-order",
    summary="Pay Order with Wallet",
    description="Pay for a pending order using the wholesaler's wallet balance."
)
async def pay_order_with_wallet(
    request_data: PayOrderRequest,
    current_user: CurrentUser,
    db: db_dependency,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Wholesaler pays for an order directly using their wallet balance"""
    if current_user.role != UserRole.WHOLESALER:
        raise HTTPException(
            status_code=403,
            detail="Only wholesalers can pay for orders"
        )
    
    # 1. Fetch Order and verify owner
    order = db.exec(select(Order).where(Order.id == request_data.order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.wholesaler_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this order")
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be paid. Current status: {order.status.value}"
        )
    
    # 2. Check Wholesaler wallet balance
    wholesaler_wallet = get_or_create_wallet(db, current_user.id)
    if wholesaler_wallet.balance < order.total_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient wallet balance. Required: ₦{order.total_amount}, Available: ₦{wholesaler_wallet.balance}"
        )
    
    # 3. Fetch Distributor wallet
    distributor = db.exec(select(User).where(User.id == order.distributor_id)).first()
    if not distributor:
        raise HTTPException(status_code=404, detail="Distributor user not found")
    
    distributor_wallet = get_or_create_wallet(db, distributor.id)
    
    # 4. Generate transaction references
    debit_ref = f"wpay_deb_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
    credit_ref = f"wpay_cred_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
    
    # 5. Process Ledger entries and wallet updates
    # Wholesaler Debit
    wholesaler_wallet.balance -= order.total_amount
    db.add(wholesaler_wallet)

    wholesaler_tx = WalletTransaction(
        wallet_id=wholesaler_wallet.id,
        amount=order.total_amount,
        type=TransactionType.DEBIT,
        purpose=TransactionPurpose.PAYMENT,
        status=TransactionStatus.COMPLETED,
        reference=debit_ref,
        description=f"Payment for Order #{order.order_number}",
        available_at=datetime.utcnow()
    )
    db.add(wholesaler_tx)

    # Distributor Credit (Locked for 24 hours)
    distributor_wallet.balance += order.total_amount
    db.add(distributor_wallet)

    distributor_tx = WalletTransaction(
        wallet_id=distributor_wallet.id,
        amount=order.total_amount,
        type=TransactionType.CREDIT,
        purpose=TransactionPurpose.PAYMENT,
        status=TransactionStatus.COMPLETED,
        reference=credit_ref,
        description=f"Received payment for Order #{order.order_number}",
        available_at=datetime.utcnow() + timedelta(hours=24) # 24-hour dynamic clearance lock
    )
    db.add(distributor_tx)

    # 6. Update order status and create Payment log
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(pytz.timezone('Africa/Lagos')).replace(tzinfo=None)
    db.add(order)

    new_payment = Payment(
        order_number=order.order_number,
        wholesaler_name=current_user.full_name,
        amount=order.total_amount,
        reference_number=debit_ref,
        status=PaymentStatus.COMPLETED,
        distributor_id=order.distributor_id,
        order_id=order.id,
        payment_method="wallet",
        initiated_at=datetime.utcnow()
    )
    db.add(new_payment)
    
    db.commit()

    # Log to audit trail
    background_tasks.add_task(
        audit_action,
        user_id=current_user.id,
        user_email=current_user.email,
        action_type="WALLET_PAY_ORDER",
        entity_type="Order",
        entity_id=str(order.id),
        old_value={"status": "PENDING"},
        new_value={
            "status": "PAID",
            "order_number": order.order_number,
            "amount": str(order.total_amount),
            "reference": debit_ref
        },
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")
    )

    return {"status": "success", "message": "Order paid successfully via wallet"}


@v1_wallet.post(
    "/withdraw",
    summary="Withdraw Funds to Bank Account",
    description="Initiate withdrawal from distributor's cleared wallet balance to their registered bank account via Paystack."
)
async def withdraw_distributor_funds(
    request_data: WithdrawRequest,
    current_user: CurrentUser,
    db: db_dependency,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Distributor withdraws cleared/available funds to their verified bank account"""
    if current_user.role != UserRole.DISTRIBUTOR:
        raise HTTPException(
            status_code=403,
            detail="Only distributors can withdraw funds"
        )
    
    # 1. Check if bank account is active on profile
    distributor_profile = db.exec(
        select(DistributorProfile).where(DistributorProfile.user_id == current_user.id)
    ).first()
    
    if not distributor_profile or not distributor_profile.is_bank_active:
        raise HTTPException(
            status_code=400,
            detail="You must verify and activate your settlement bank account details before requesting withdrawals"
        )
    
    # 2. Get wallet and compute withdrawable balance
    wallet = get_or_create_wallet(db, current_user.id)
    
    # Compute withdrawable balance
    now = datetime.utcnow()
    credits_stmt = select(WalletTransaction).where(
        WalletTransaction.wallet_id == wallet.id,
        WalletTransaction.type == TransactionType.CREDIT,
        WalletTransaction.status == TransactionStatus.COMPLETED,
        WalletTransaction.available_at <= now
    )
    credits_sum = sum(tx.amount for tx in db.exec(credits_stmt).all())

    debits_stmt = select(WalletTransaction).where(
        WalletTransaction.wallet_id == wallet.id,
        WalletTransaction.type == TransactionType.DEBIT,
        WalletTransaction.status.in_([TransactionStatus.COMPLETED, TransactionStatus.PENDING])
    )
    debits_sum = sum(tx.amount for tx in db.exec(debits_stmt).all())

    withdrawable_balance = max(Decimal("0.00"), credits_sum - debits_sum)
    withdrawable_balance = min(withdrawable_balance, wallet.balance)

    if withdrawable_balance < request_data.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient withdrawable balance. Available: ₦{withdrawable_balance}, Requested: ₦{request_data.amount}"
        )
    
    # 3. Resolve bank name to bank code
    bank_code = await get_bank_code_by_name(distributor_profile.bank_name)
    if not bank_code:
        raise HTTPException(
            status_code=400,
            detail=f"Could not resolve bank code for bank: '{distributor_profile.bank_name}'"
        )

    # 4. Create Transfer Recipient on Paystack
    token = settings.PAYSTACK_SECRET_KEY
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        recipient_payload = {
            "type": "nuban",
            "name": distributor_profile.account_name,
            "account_number": distributor_profile.account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        recipient_response = await client.post(
            "https://api.paystack.co/transferrecipient",
            json=recipient_payload,
            headers=headers
        )
    
    recipient_data = recipient_response.json()
    if recipient_response.status_code != 201 or recipient_data.get("status") is not True:
        raise HTTPException(
            status_code=400,
            detail=f"Paystack recipient creation failed: {recipient_data.get('message', 'Unknown Error')}"
        )
    
    recipient_code = recipient_data["data"]["recipient_code"]
    reference = f"wwith_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"

    # 5. Lock funds in ledger (PENDING DEBIT)
    wallet.balance -= request_data.amount
    db.add(wallet)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=request_data.amount,
        type=TransactionType.DEBIT,
        purpose=TransactionPurpose.WITHDRAWAL,
        status=TransactionStatus.PENDING,
        reference=reference,
        description=f"Withdrawal to {distributor_profile.bank_name} ({distributor_profile.account_number})",
        available_at=datetime.utcnow()
    )
    db.add(tx)
    db.commit()

    # 6. Trigger Paystack Transfer
    async with httpx.AsyncClient() as client:
        transfer_payload = {
            "source": "balance",
            "amount": int(request_data.amount * 100), # in kobo
            "recipient": recipient_code,
            "reason": "SalesFunnel Wallet Payout",
            "reference": reference
        }
        transfer_response = await client.post(
            "https://api.paystack.co/transfer",
            json=transfer_payload,
            headers=headers
        )
    
    transfer_data = transfer_response.json()
    if transfer_response.status_code != 200 or transfer_data.get("status") is not True:
        # Revert funds if transfer failed immediately
        wallet.balance += request_data.amount
        tx.status = TransactionStatus.FAILED
        db.add(wallet)
        db.add(tx)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Paystack transfer request failed: {transfer_data.get('message', 'Unknown Error')}"
        )

    background_tasks.add_task(
        audit_action,
        user_id=current_user.id,
        user_email=current_user.email,
        action_type="WITHDRAW_FUNDS",
        entity_type="WalletTransaction",
        entity_id=str(tx.id),
        old_value=None,
        new_value={
            "amount": str(request_data.amount),
            "reference": reference,
            "recipient_code": recipient_code,
            "paystack_transfer_id": transfer_data["data"].get("transfer_code")
        },
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")
    )

    return {"status": "success", "message": "Withdrawal processing initiated successfully", "reference": reference}

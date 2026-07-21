# internal imports
from app.core.config import settings
from app.core.helpers import audit_action
from app.core.dependencies import CurrentUser, DBSession
from app.models.order import Order, OrderStatus
from app.models.distributor_profile import DistributorProfile
from app.models.wholesaler_profile import WholesalerProfile
from app.models.user import User, UserRole
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.payment import Payment, PaymentStatus
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction, TransactionStatus, TransactionType, TransactionPurpose
from decimal import Decimal
import uuid

# external imports
import json
import httpx
import hmac
import hashlib
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc
from sqlmodel import select
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from datetime import datetime
import pytz

v1_payment = APIRouter(prefix="/v1/payment", tags=["v1_payment"])
db_dependency = DBSession

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

# Response Schema
class InitializePaymentResponse(BaseModel):
    status: str
    message: str
    data: dict | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Payment initialization successful",
                "data": {
                    "authorization_url": "https://checkout.paystack.com/001122334455",
                    "access_code": "001122334455",
                    "reference": "PAY-REF-998822"
                }
            }
        }
    )

@v1_payment.post(
    "/initialize", 
    response_model=InitializePaymentResponse,
    summary="Initialize Paystack Payment Checkout",
    description="Initialize a Paystack payment session for the logged-in wholesaler's latest order."
)
async def initialize_payment( 
    current_user: CurrentUser,
    db: db_dependency,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Initialize a Paystack transaction and send payment request to customer.
    
    Args:
        email: Customer email address
        amount: Amount in kobo (100 kobo = 1 naira)
        subaccount: Distributor's Paystack subaccount code for split payment
    
    Returns:
        Authorization URL to redirect customer for payment
    """

    # Validate Paystack secret key is configured
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Paystack secret key not configured"
        )
    
    # Get user id and email address from jwt token
    id = current_user.id
    email = current_user.email

    # Get the last order made by the user (wholesaler)
    statement = select(Order)\
        .where(Order.wholesaler_id == id)\
        .order_by(desc(Order.created_at)) # type: ignore
    
    order = db.exec(statement).first()
    
    if not order:
        raise HTTPException(
            status_code=404,
            detail="No orders found for this wholesaler"
        )
    
    print(order)

    # Get order amount from the order data
    amount = order.total_amount
    paystack_amount = int(amount*100)

    print("Distributor_id: ", order.distributor_id)
   
   # Get distributor subaccount_code
    statement = select(DistributorProfile)\
        .where(DistributorProfile.user_id == order.distributor_id)
    
    distributor = db.exec(statement).first()
    if not distributor:
        raise HTTPException(
            status_code=404,
            detail="Error! distributor was not found"
        )

    subaccount_code = distributor.subaccount_code
    
    # Prepare Paystack request payload
    payload = {
        "email": email,
        "amount": paystack_amount
    }
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make async request to Paystack
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.PAYSTACK_API_URL}/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=10.0
            )
        
        # Parse Paystack response
        paystack_data = response.json()
        
        # Check if Paystack returned success
        if paystack_data.get("status") == True:
            # Log to audit trail
            background_tasks.add_task(
                audit_action,
                user_id=current_user.id,
                user_email=current_user.email,
                action_type="INITIALIZE",
                entity_type="Payment",
                entity_id=str(order.id),
                old_value=None,
                new_value={
                    "order_number": order.order_number,
                    "amount": str(amount),
                    "reference": paystack_data["data"]["reference"]
                },
                ip_address=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", "")
            )
            
            return InitializePaymentResponse(
                status="success",
                message="Payment initialization successful",
                data={
                    "authorization_url": paystack_data["data"]["authorization_url"],
                    "access_code": paystack_data["data"]["access_code"],
                    "reference": paystack_data["data"]["reference"]
                }
            )
        else:
            error_message = paystack_data.get("message", "Unknown error")
            raise HTTPException(
                status_code=400,
                detail=f"Paystack error: {error_message}"
            )
    
    except httpx.RequestError as e:
        print(f"ERROR: Failed to connect to Paystack: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to Paystack"
        )
    except Exception as e:
        print(f"ERROR: Payment initialization failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Payment initialization failed: {str(e)}"
        )

@v1_payment.post("/paystack-hook")
async def paystack_webhook(
    request: Request, 
    db: db_dependency,
    background_tasks: BackgroundTasks
):
    """
    Simple webhook endpoint that receives Paystack payment events
    and processes them accordingly.
    """
    try:
        # Get the raw data from Paystack
        body = await request.body()
        data = json.loads(body)      
        print(data)  
        event = data.get("event")
        event_data = data.get('data', {})

        if event == "charge.success":
            # gets the wholesaler email and from the webhook payload
            customer = event_data.get('customer', {})
            email = customer.get('email')

            reference = event_data.get("reference", {})
            amount = int(event_data.get("amount"))
            real_amount = amount/100
            payment_date = event_data.get("paid_at", {})
            channel = event_data.get("channel", {})
            metadata = event_data.get("metadata") or {}

            # Check if this is a wallet funding charge or dedicated virtual account deposit
            authorization = event_data.get("authorization") or {}
            is_dva_deposit = (
                channel in ["dedicated_nul", "dedicated_account"] 
                or authorization.get("channel") in ["dedicated_nul", "dedicated_account"]
            )

            if metadata.get("type") == "wallet_funding" or is_dva_deposit:
                wholesaler_id = metadata.get("wholesaler_id")
                
                # Fetch transaction if already created (pre-initialized funding)
                tx = db.exec(select(WalletTransaction).where(WalletTransaction.reference == reference)).first()
                if tx:
                    if tx.status == TransactionStatus.PENDING:
                        tx.status = TransactionStatus.COMPLETED
                        db.add(tx)
                        
                        # Update wholesaler's wallet
                        wallet = db.exec(select(Wallet).where(Wallet.id == tx.wallet_id)).first()
                        if wallet:
                            wallet.balance += Decimal(str(real_amount))
                            db.add(wallet)
                            
                        db.commit()
                        
                        background_tasks.add_task(
                            audit_action,
                            user_id=uuid.UUID(wholesaler_id) if wholesaler_id else None,
                            user_email=email,
                            action_type="CONFIRM_FUNDING",
                            entity_type="WalletTransaction",
                            entity_id=str(tx.id),
                            old_value={"status": "PENDING"},
                            new_value={
                                "status": "COMPLETED",
                                "amount": str(real_amount),
                                "reference": reference
                            },
                            ip_address=request.client.host if request.client else "",
                            user_agent=request.headers.get("user-agent", "")
                        )
                    return {"status": "received", "message": "Wallet funding charge.success processed"}

                # If no existing pending transaction, handle direct DVA deposit
                wholesaler = db.exec(select(User).where(User.email == email)).first()
                if wholesaler and wholesaler.role == UserRole.WHOLESALER:
                    wallet = db.exec(select(Wallet).where(Wallet.user_id == wholesaler.id)).first()
                    if not wallet:
                        wallet = Wallet(user_id=wholesaler.id, balance=Decimal("0.00"))
                        db.add(wallet)
                        db.commit()

                    wallet.balance += Decimal(str(real_amount))
                    db.add(wallet)

                    new_tx = WalletTransaction(
                        wallet_id=wallet.id,
                        amount=Decimal(str(real_amount)),
                        type=TransactionType.CREDIT,
                        purpose=TransactionPurpose.FUNDING,
                        status=TransactionStatus.COMPLETED,
                        reference=reference,
                        description="Dedicated virtual account transfer deposit"
                    )
                    db.add(new_tx)
                    db.commit()

                    background_tasks.add_task(
                        audit_action,
                        user_id=wholesaler.id,
                        user_email=wholesaler.email,
                        action_type="CONFIRM_DVA_FUNDING",
                        entity_type="WalletTransaction",
                        entity_id=str(new_tx.id),
                        old_value=None,
                        new_value={
                            "status": "COMPLETED",
                            "amount": str(real_amount),
                            "reference": reference,
                            "channel": channel
                        },
                        ip_address=request.client.host if request.client else "",
                        user_agent=request.headers.get("user-agent", "")
                    )
                    return {"status": "received", "message": "Dedicated virtual account deposit processed successfully"}

            # Otherwise, it's standard order payment
            wholesaler = db.exec(select(User).where(User.email == email)).first()
            if not wholesaler:
                return {"status": "error", "message": "User not found"}
            
            # gets the last order made by the wholesaler
            last_order = db.exec(
                select(Order)
                .where(Order.wholesaler_id == wholesaler.id)
                .order_by(desc(Order.created_at))  # type: ignore
            ).first()

            # Check if order exists BEFORE making changes
            if not last_order:
                return {"status": "error", "message": "No order found for this customer"}

            # changes the status of the order made by the wholesaler to paid
            last_order.status = OrderStatus.PAID
            last_order.paid_at = datetime.now(pytz.timezone('Africa/Lagos')).replace(tzinfo=None)
            db.add(last_order)
            db.commit()

            # gets all order items belonging to the last order
            order_items = db.exec(
                select(OrderItem)
                .where(OrderItem.order_id == last_order.id)
            ).all()

            # Reduce stock for each product in the order
            for order_item in order_items:
                product = db.exec(
                    select(Product)
                    .where(Product.id == order_item.product_id)
                ).first()

                if product:
                    product.stock_quantity -= order_item.quantity
                    db.add(product)

            db.commit()

            # preparing part of the payment data
            new_payment_data = {
                "order_number": last_order.order_number,
                "wholesaler_name": wholesaler.full_name,
                "amount": Decimal(str(real_amount)),
                "reference_number": reference,
                "status": PaymentStatus.COMPLETED, 
                "distributor_id": last_order.distributor_id
            }

            # creating a payment row in the db
            new_payment = Payment(
                **new_payment_data,
                order_id=last_order.id,
                payment_method=channel,
                initiated_at=datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
                )
            db.add(new_payment)
            db.commit()
            
            # Log to audit trail
            background_tasks.add_task(
                audit_action,
                user_id=wholesaler.id,
                user_email=wholesaler.email,
                action_type="CONFIRM",
                entity_type="Payment",
                entity_id=str(last_order.id),
                old_value={"status": "PENDING"},
                new_value={
                    "status": "PAID",
                    "order_number": last_order.order_number,
                    "amount": str(real_amount),
                    "reference": reference,
                    "channel": channel
                },
                ip_address=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", "")
            )
            return {"status": "received", "message": "Order payment charge.success processed"}

        elif event == "transfer.success":
            transfer_ref = event_data.get("reference")
            tx = db.exec(select(WalletTransaction).where(WalletTransaction.reference == transfer_ref)).first()
            if tx and tx.status == TransactionStatus.PENDING:
                tx.status = TransactionStatus.COMPLETED
                db.add(tx)
                
                wallet = db.exec(select(Wallet).where(Wallet.id == tx.wallet_id)).first()
                user_id = wallet.user_id if wallet else None
                user_email = ""
                if user_id:
                    user = db.exec(select(User).where(User.id == user_id)).first()
                    user_email = user.email if user else ""
                
                db.commit()
                
                background_tasks.add_task(
                    audit_action,
                    user_id=user_id,
                    user_email=user_email,
                    action_type="CONFIRM_WITHDRAWAL",
                    entity_type="WalletTransaction",
                    entity_id=str(tx.id),
                    old_value={"status": "PENDING"},
                    new_value={"status": "COMPLETED", "reference": transfer_ref},
                    ip_address=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", "")
                )
            return {"status": "received", "message": "transfer.success processed"}

        elif event == "transfer.failed":
            transfer_ref = event_data.get("reference")
            tx = db.exec(select(WalletTransaction).where(WalletTransaction.reference == transfer_ref)).first()
            if tx and tx.status == TransactionStatus.PENDING:
                tx.status = TransactionStatus.FAILED
                db.add(tx)
                
                wallet = db.exec(select(Wallet).where(Wallet.id == tx.wallet_id)).first()
                user_id = None
                user_email = ""
                if wallet:
                    wallet.balance += tx.amount
                    db.add(wallet)
                    user_id = wallet.user_id
                    user = db.exec(select(User).where(User.id == user_id)).first()
                    user_email = user.email if user else ""
                
                db.commit()
                
                background_tasks.add_task(
                    audit_action,
                    user_id=user_id,
                    user_email=user_email,
                    action_type="FAIL_WITHDRAWAL",
                    entity_type="WalletTransaction",
                    entity_id=str(tx.id),
                    old_value={"status": "PENDING"},
                    new_value={"status": "FAILED", "reference": transfer_ref, "message": "Funds reverted due to transfer failure"},
                    ip_address=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", "")
                )
            return {"status": "received", "message": "transfer.failed processed"}

        elif event == "dedicatedaccount.assign.success":
            customer = event_data.get("customer", {})
            email = customer.get("email")

            dedicated_account = event_data.get("dedicated_account", {})
            virtual_account_id = dedicated_account.get("id") or dedicated_account.get("dedicated_account_id")

            if not email or not virtual_account_id:
                return {"status": "error", "message": "Missing customer email or virtual account ID in payload"}

            user = db.exec(select(User).where(User.email == email)).first()
            if not user:
                return {"status": "error", "message": "User not found for dedicated account assignment"}

            if user.role != UserRole.WHOLESALER:
                return {"status": "error", "message": "Only wholesalers can have dedicated virtual accounts"}

            wholesaler_profile = db.exec(
                select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
            ).first()

            if not wholesaler_profile:
                return {"status": "error", "message": "Wholesaler profile not found"}

            wholesaler_profile.paystack_dedicated_account_id = str(virtual_account_id)
            db.add(wholesaler_profile)
            db.commit()

            background_tasks.add_task(
                audit_action,
                user_id=user.id,
                user_email=email,
                action_type="ASSIGN_DEDICATED_ACCOUNT",
                entity_type="WholesalerProfile",
                entity_id=str(wholesaler_profile.id),
                old_value=None,
                new_value={"paystack_dedicated_account_id": str(virtual_account_id)},
                ip_address=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", "")
            )

            return {"status": "received", "message": "dedicatedaccount.assign.success processed"}

        return {"status": "received", "message": f"Webhook event '{event}' ignored"}
        
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON received from Paystack")
        return {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        print(f"ERROR processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@v1_payment.post("/bank-list")
async def list_of_supported_banks():
    token = settings.PAYSTACK_SECRET_KEY
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.paystack.co/bank", 
            headers=headers
        )
    bank_list = response.json()["data"]

    banks = []
    for bank in bank_list:
        single_bank = {"name": bank["name"], "code" : bank["code"]}
        banks.append(single_bank)

    return {"list_of_banks": banks}

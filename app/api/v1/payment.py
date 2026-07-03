# internal imports
from app.core.config import settings
from app.core.helpers import audit_action
from app.core.dependencies import CurrentUser, DBSession
from app.models.order import Order, OrderStatus
from app.models.distributor_profile import DistributorProfile
from app.models.user import User
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.payment import Payment, PaymentStatus
from decimal import Decimal

# external imports
import json
import httpx
import hmac
import hashlib
from pydantic import BaseModel
from sqlalchemy import desc
from sqlmodel import select
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from datetime import datetime
import pytz

v1_payment = APIRouter(prefix="/v1/payment", tags=["v1_payment"])
db_dependency = DBSession

PAYSTACK_API_URL: str = "https://api.paystack.co"
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

# Response Schema
class InitializePaymentResponse(BaseModel):
    status: str
    message: str
    data: dict | None = None

@v1_payment.post("/initialize", response_model=InitializePaymentResponse)
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
        "amount": paystack_amount,
        "subaccount": subaccount_code
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
    and prints the data to console.
    
    Paystack will send POST requests to this endpoint for payment events:
    - charge.success
    - charge.failed
    - transfer.success
    - transfer.failed
    - etc.
    """
    try:
        # Get the raw data from Paystack
        body = await request.body()
        data = json.loads(body)        

        # gets the wholesaler email and from the webhook payload
        customer = data.get('data', {}).get('customer', {})
        email = customer.get('email')

        # gets additional data from webhook payload
        event_data = data.get('data', {})

        reference = event_data.get("reference", {})
        amount = int(event_data.get("amount"))
        real_amount = amount/100
        payment_date = event_data.get("paid_at", {})
        channel = event_data.get("channel", {})

        
        # gets the user by email first
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
            "status": PaymentStatus.PENDING, 
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
        
        # Return success response to Paystack
        return {"status": "received", "message": "Webhook data received successfully"}
        
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON received from Paystack")
        return {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        print(f"ERROR processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@v1_payment.post("/nomba-hook")
async def nomba_webhook(
    request: Request,
    db: db_dependency,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint that receives Nomba payment events.
    Currently commented out to only print the payload.
    """
    try:
        # Get signature from header
        received_signature = request.headers.get("nomba-signature")
        if not received_signature:
            print("ERROR: Missing nomba-signature header")
            raise HTTPException(status_code=400, detail="Missing nomba-signature header")

        # Get raw request body
        body_bytes = await request.body()

        # Compute signature
        computed_signature = hmac.new(
            settings.NOMBA_SIGNING_KEY.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        # Validate signature
        if not hmac.compare_digest(computed_signature, received_signature):
            print("ERROR: Nomba signature mismatch")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse and print payload
        payload = json.loads(body_bytes)
        print("Nomba Webhook Payload:", payload)

        # event_type = payload.get("eventType")
        # event_data = payload.get("data", {})
        # 
        # if event_type != "payment_success":
        #     print(f"INFO: Ignoring Nomba webhook event type: {event_type}")
        #     return {"status": "received", "message": f"Event type {event_type} ignored"}
        # 
        # # Extract transaction and order info
        # reference = event_data.get("transactionId") or event_data.get("orderReference")
        # if not reference:
        #     print("ERROR: Missing transaction reference in Nomba webhook payload")
        #     return {"status": "error", "message": "Missing reference"}
        # 
        # # Check for duplicate webhook processing
        # existing_payment = db.exec(
        #     select(Payment).where(Payment.reference_number == reference)
        # ).first()
        # if existing_payment:
        #     print(f"INFO: Nomba webhook already processed for reference: {reference}")
        #     return {"status": "received", "message": "Webhook already processed"}
        # 
        # # Find the order
        # last_order = None
        # wholesaler = None
        # order_reference = event_data.get("orderReference")
        # 
        # if order_reference:
        #     last_order = db.exec(
        #         select(Order).where(Order.order_number == order_reference)
        #     ).first()
        #     if last_order:
        #         wholesaler = db.exec(
        #             select(User).where(User.id == last_order.wholesaler_id)
        #         ).first()
        # 
        # # Fallback to customer email lookup if order not found by reference
        # if not last_order:
        #     customer = event_data.get("customer", {})
        #     email = customer.get("email")
        #     if email:
        #         wholesaler = db.exec(select(User).where(User.email == email)).first()
        #         if wholesaler:
        #             last_order = db.exec(
        #                 select(Order)
        #                 .where(Order.wholesaler_id == wholesaler.id)
        #                 .order_by(desc(Order.created_at))  # type: ignore
        #             ).first()
        # 
        # if not last_order:
        #     print("ERROR: Order not found for Nomba webhook")
        #     return {"status": "error", "message": "Order not found"}
        # 
        # if not wholesaler:
        #     # Fallback to get wholesaler from order
        #     wholesaler = db.exec(
        #         select(User).where(User.id == last_order.wholesaler_id)
        #     ).first()
        # 
        # # Parse amount
        # amount_raw = event_data.get("amount")
        # try:
        #     real_amount = float(amount_raw)
        # except (ValueError, TypeError):
        #     real_amount = float(last_order.total_amount)
        # 
        # amount_decimal = Decimal(str(real_amount))
        # 
        # # Update order status if not already paid
        # if last_order.status != OrderStatus.PAID:
        #     last_order.status = OrderStatus.PAID
        #     last_order.paid_at = datetime.now(pytz.timezone('Africa/Lagos')).replace(tzinfo=None)
        #     db.add(last_order)
        #     db.commit()
        # 
        #     # Reduce stock for each product in the order
        #     order_items = db.exec(
        #         select(OrderItem).where(OrderItem.order_id == last_order.id)
        #     ).all()
        # 
        #     for order_item in order_items:
        #         product = db.exec(
        #             select(Product).where(Product.id == order_item.product_id)
        #         ).first()
        #         if product:
        #             product.stock_quantity -= order_item.quantity
        #             db.add(product)
        # 
        #     db.commit()
        # 
        # # Create payment record
        # channel = event_data.get("paymentMethod") or event_data.get("channel") or "nomba"
        # 
        # # Get timestamp
        # timestamp_str = request.headers.get("nomba-timestamp") or payload.get("timestamp")
        # initiated_at = datetime.utcnow()
        # if timestamp_str:
        #     try:
        #         clean_timestamp = timestamp_str.replace('Z', '+00:00')
        #         initiated_dt = datetime.fromisoformat(clean_timestamp)
        #         if initiated_dt.tzinfo is not None:
        #             initiated_at = initiated_dt.astimezone(pytz.utc).replace(tzinfo=None)
        #         else:
        #             initiated_at = initiated_dt
        #     except Exception:
        #         pass
        # 
        # new_payment = Payment(
        #     order_id=last_order.id,
        #     distributor_id=last_order.distributor_id,
        #     reference_number=reference,
        #     amount=amount_decimal,
        #     payment_method=channel,
        #     status=PaymentStatus.VERIFIED,
        #     order_number=last_order.order_number,
        #     wholesaler_name=wholesaler.full_name if wholesaler else "Unknown Wholesaler",
        #     initiated_at=initiated_at
        # )
        # db.add(new_payment)
        # db.commit()
        # 
        # # Log to audit trail
        # if wholesaler:
        #     background_tasks.add_task(
        #         audit_action,
        #         user_id=wholesaler.id,
        #         user_email=wholesaler.email,
        #         action_type="CONFIRM",
        #         entity_type="Payment",
        #         entity_id=str(last_order.id),
        #         old_value={"status": "PENDING"},
        #         new_value={
        #             "status": "PAID",
        #             "order_number": last_order.order_number,
        #             "amount": str(real_amount),
        #             "reference": reference,
        #             "channel": channel
        #         },
        #         ip_address=request.client.host if request.client else "",
        #         user_agent=request.headers.get("user-agent", "")
        #     )
        
        return {"status": "received", "message": "Webhook payload received"}

    except json.JSONDecodeError:
        print("ERROR: Invalid JSON received from Nomba")
        return {"status": "error", "message": "Invalid JSON"}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"ERROR processing Nomba webhook: {str(e)}")
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
        banks.append(bank["name"])

    return {"list_of_banks": banks}

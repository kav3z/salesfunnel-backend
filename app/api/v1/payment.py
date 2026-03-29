# internal imports
from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession
from app.models.order import Order, OrderStatus
from app.models.distributor_profile import DistributorProfile
from app.models.user import User
from app.models.order_item import OrderItem
from app.models.product import Product

# external imports
import json
import httpx
from pydantic import BaseModel
from sqlalchemy import desc
from sqlmodel import select
from fastapi import APIRouter, HTTPException, Request

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
    db: db_dependency  # Add this parameter
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
async def paystack_webhook(request: Request, db: db_dependency):
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

        # gets the wholesaler email from the webhook payload
        customer = data.get('data', {}).get('customer', {})
        email = customer.get('email')
        
        # gets the last order made by the wholesaler
        last_order = db.exec(
            select(Order)
            .join(User, Order.wholesaler_id == User.id) # type: ignore
            .where(User.email == email)
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
        
        # Return success response to Paystack
        return {"status": "received", "message": "Webhook data received successfully"}
        
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON received from Paystack")
        return {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        print(f"ERROR processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}
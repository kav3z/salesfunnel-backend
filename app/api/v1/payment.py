# internal imports
from app.core.config import settings

# external imports
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.core.config import settings
from decimal import Decimal

v1_payment = APIRouter(prefix="/v1/payment", tags=["v1_payment"])

PAYSTACK_API_URL: str = "https://api.paystack.co"
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
# Request Schema
class InitializePaymentRequest(BaseModel):
    email: EmailStr
    amount: int  # in kobo (e.g., 20000 = 200 naira)
    subaccount: str  # Distributor's Paystack subaccount code

# Response Schema
class InitializePaymentResponse(BaseModel):
    status: str
    message: str
    data: dict = None

@v1_payment.post("/initialize", response_model=InitializePaymentResponse)
async def initialize_payment(request: InitializePaymentRequest):
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
    
    # Prepare Paystack request payload
    payload = {
        "email": request.email,
        "amount": request.amount,
        "subaccount": request.subaccount
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

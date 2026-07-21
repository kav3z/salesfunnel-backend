from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from uuid import UUID


class DistributorRegisterRequest(BaseModel):
    """Complete Distributor Registration Request"""
    password: str = Field(..., min_length=8, max_length=72, description="Account Password")
    business_name: str = Field(..., min_length=2, max_length=255, description="Business Name")
    business_address: str = Field(..., min_length=10, max_length=500, description="Business Address")
    business_phone: str = Field(..., min_length=10, max_length=20, description="Business Phone Number")
    business_email: EmailStr = Field(..., description="Business Email Address")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "password": "Password123!",
                "business_name": "Prime Distribution Hub",
                "business_address": "45 Warehouse Road, Apapa, Lagos",
                "business_phone": "+2348098765432",
                "business_email": "distributor@example.com"
            }
        }
    )


class DistributorResponse(BaseModel):
    """Distributor Registration Response"""
    id: str
    user_id: str
    business_name: str
    cac_registration_number: Optional[str] = None
    business_address: str
    business_phone: str
    business_email: str
    tin: Optional[str] = None
    owner_full_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    is_verified: bool
    cac_certificate_url: Optional[str] = None
    tin_certificate_url: Optional[str] = None
    utility_bill_url: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                "user_id": "a12c71c9-e9e4-49d8-96be-8248f20d5a99",
                "business_name": "Prime Distribution Hub",
                "cac_registration_number": "RC654321",
                "business_address": "45 Warehouse Road, Apapa, Lagos",
                "business_phone": "+2348098765432",
                "business_email": "distributor@example.com",
                "tin": "TIN123456789",
                "owner_full_name": None,
                "owner_phone": None,
                "owner_email": None,
                "bank_name": None,
                "account_name": None,
                "account_number": None,
                "is_verified": False,
                "cac_certificate_url": None,
                "tin_certificate_url": None,
                "utility_bill_url": None
            }
        }
    )


class DistributorListResponse(BaseModel):
    """Distributor List Item Response"""
    id: str
    user_id: str
    business_name: str
    business_address: str
    business_phone: str
    business_email: str
    is_verified: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                "user_id": "a12c71c9-e9e4-49d8-96be-8248f20d5a99",
                "business_name": "Prime Distribution Hub",
                "business_address": "45 Warehouse Road, Apapa, Lagos",
                "business_phone": "+2348098765432",
                "business_email": "distributor@example.com",
                "is_verified": True
            }
        }
    )

class MonthlyRevenueItem(BaseModel):
    """Monthly revenue data point"""
    month: str = Field(..., description="Month abbreviation (Jan, Feb, Mar, etc.)")
    revenue: float = Field(..., description="Total revenue for the month")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "month": "Jul",
                "revenue": 3450000.50
            }
        }
    )


class DistributorDashboardResponse(BaseModel):
    """Distributor Dashboard Statistics Response"""
    total_revenue: float = Field(..., description="Total revenue from all paid orders")
    total_products: int = Field(..., description="Total number of products uploaded by distributor")
    orders_by_status: dict[str, int] = Field(..., description="Count of orders by status (paid, completed)")
    monthly_revenue_trend: List[MonthlyRevenueItem] = Field(..., description="Monthly revenue trend data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_revenue": 14500000.00,
                "total_products": 28,
                "orders_by_status": {
                    "paid": 12,
                    "completed": 45,
                    "pending": 3
                },
                "monthly_revenue_trend": [
                    {"month": "May", "revenue": 4100000.00},
                    {"month": "Jun", "revenue": 5200000.00},
                    {"month": "Jul", "revenue": 5200000.00}
                ]
            }
        }
    )

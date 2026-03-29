from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID


class DistributorRegisterRequest(BaseModel):
    """Complete Distributor Registration Request"""
    # Account credentials
    password: str = Field(..., min_length=8, max_length=72, description="Account Password")
    
    # Company Information
    business_name: str = Field(..., min_length=2, max_length=255)
    cac_registration_number: str = Field(..., min_length=5, max_length=50)
    business_address: str = Field(..., min_length=10, max_length=500)
    business_phone: str = Field(..., min_length=10, max_length=20)
    business_email: EmailStr
    
    # Tax & Compliance
    tin: str = Field(..., min_length=5, max_length=50)
    
    # Owner/Director Details
    owner_full_name: str = Field(..., min_length=2, max_length=255)
    owner_phone: str = Field(..., min_length=10, max_length=20)
    owner_email: EmailStr
    
    # Bank Details (for payment settlement)
    bank_name: str = Field(..., min_length=2, max_length=100)
    account_name: str = Field(..., min_length=2, max_length=255)
    account_number: str = Field(..., min_length=10, max_length=20)


class DistributorResponse(BaseModel):
    """Distributor Registration Response"""
    id: str
    user_id: str
    business_name: str
    cac_registration_number: str
    business_address: str
    business_phone: str
    business_email: str
    tin: str
    owner_full_name: str
    owner_phone: str
    owner_email: str
    bank_name: str
    account_name: str
    account_number: str
    is_verified: bool
    cac_certificate_url: Optional[str] = None
    tin_certificate_url: Optional[str] = None
    utility_bill_url: Optional[str] = None


class DistributorListResponse(BaseModel):
    """Distributor List Item Response"""
    id: str
    user_id: str
    business_name: str
    business_address: str
    business_phone: str
    business_email: str
    is_verified: bool

class MonthlyRevenueItem(BaseModel):
    """Monthly revenue data point"""
    month: str = Field(..., description="Month abbreviation (Jan, Feb, Mar, etc.)")
    revenue: float = Field(..., description="Total revenue for the month")


class DistributorDashboardResponse(BaseModel):
    """Distributor Dashboard Statistics Response"""
    total_revenue: float = Field(..., description="Total revenue from all paid orders")
    total_products: int = Field(..., description="Total number of products uploaded by distributor")
    orders_by_status: dict[str, int] = Field(..., description="Count of orders by status (paid, completed)")
    monthly_revenue_trend: list[MonthlyRevenueItem] = Field(..., description="Monthly revenue trend data")

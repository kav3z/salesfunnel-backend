from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from uuid import UUID
from fastapi import UploadFile


class CompanyInfo(BaseModel):
    """Company Information"""
    business_name: str = Field(..., min_length=2, max_length=255, description="Registered Business Name")
    cac_registration_number: str = Field(..., min_length=5, max_length=50, description="CAC Registration Number")
    business_address: str = Field(..., min_length=10, max_length=500, description="Business Address")
    business_phone: str = Field(..., min_length=10, max_length=20, description="Business Phone Number")
    business_email: EmailStr = Field(..., description="Business Email")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "business_name": "Apex Wholesale Ltd",
                "cac_registration_number": "RC123456",
                "business_address": "12 Commercial Avenue, Ikeja, Lagos",
                "business_phone": "+2348012345678",
                "business_email": "wholesaler@example.com"
            }
        }
    )


class TaxCompliance(BaseModel):
    """Tax & Compliance Information"""
    tin: str = Field(..., min_length=5, max_length=50, description="Tax Identification Number")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tin": "TIN987654321"
            }
        }
    )


class OwnerDetails(BaseModel):
    """Owner/Director Details"""
    full_name: str = Field(..., min_length=2, max_length=255, description="Full Name")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone Number")
    email: EmailStr = Field(..., description="Email Address")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "John Doe",
                "phone": "+2348012345678",
                "email": "johndoe@example.com"
            }
        }
    )


class BankDetails(BaseModel):
    """Bank Details"""
    bank_name: str = Field(..., min_length=2, max_length=100, description="Bank Name")
    account_name: str = Field(..., min_length=2, max_length=255, description="Account Name")
    account_number: str = Field(..., min_length=10, max_length=20, description="Account Number")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bank_name": "Access Bank",
                "account_name": "Apex Wholesale Ltd",
                "account_number": "0123456789"
            }
        }
    )


class WholesalerRegisterRequest(BaseModel):
    """Complete Wholesaler Registration Request"""
    password: str = Field(..., min_length=8, max_length=72, description="Account Password")
    business_name: str = Field(..., min_length=2, max_length=255, description="Business Name")
    business_address: str = Field(..., min_length=10, max_length=500, description="Business Address")
    business_phone: str = Field(..., min_length=10, max_length=20, description="Business Phone Number")
    business_email: EmailStr = Field(..., description="Business Email Address")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "password": "Password123!",
                "business_name": "Apex Wholesale Ltd",
                "business_address": "12 Commercial Avenue, Ikeja, Lagos",
                "business_phone": "+2348012345678",
                "business_email": "wholesaler@example.com"
            }
        }
    )


class WholesalerResponse(BaseModel):
    """Wholesaler Registration Response"""
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
                "id": "34dc8ca4-e353-416b-b5b0-643c25aa15b8",
                "user_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "business_name": "Apex Wholesale Ltd",
                "cac_registration_number": "RC123456",
                "business_address": "12 Commercial Avenue, Ikeja, Lagos",
                "business_phone": "+2348012345678",
                "business_email": "wholesaler@example.com",
                "tin": "TIN987654321",
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

class WholesalerDashboardResponse(BaseModel):
    """Wholesaler Dashboard Statistics Response"""
    orders_in_progress: int = Field(..., description="Count of orders with PAID status")
    action_required_unpaid: int = Field(..., description="Count of orders with PENDING status")
    completed_this_month_revenue: float = Field(..., description="Total revenue from completed orders this month")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orders_in_progress": 4,
                "action_required_unpaid": 2,
                "completed_this_month_revenue": 1250000.00
            }
        }
    )

from pydantic import BaseModel, EmailStr, Field
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


class TaxCompliance(BaseModel):
    """Tax & Compliance Information"""
    tin: str = Field(..., min_length=5, max_length=50, description="Tax Identification Number")


class OwnerDetails(BaseModel):
    """Owner/Director Details"""
    full_name: str = Field(..., min_length=2, max_length=255, description="Full Name")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone Number")
    email: EmailStr = Field(..., description="Email Address")


class BankDetails(BaseModel):
    """Bank Details"""
    bank_name: str = Field(..., min_length=2, max_length=100, description="Bank Name")
    account_name: str = Field(..., min_length=2, max_length=255, description="Account Name")
    account_number: str = Field(..., min_length=10, max_length=20, description="Account Number")


class WholesalerRegisterRequest(BaseModel):
    """Complete Wholesaler Registration Request"""
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
    
    # Bank Details
    bank_name: str = Field(..., min_length=2, max_length=100)
    account_name: str = Field(..., min_length=2, max_length=255)
    account_number: str = Field(..., min_length=10, max_length=20)


class WholesalerResponse(BaseModel):
    """Wholesaler Registration Response"""
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
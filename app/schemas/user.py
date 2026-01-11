# internal imports 
from app.models.user import UserRole

# external imports
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    """Token response schema with user info"""
    access_token: str
    token_type: str
    user_id: str



class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Basic user response schema"""
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool


class WholesalerProfileData(BaseModel):
    """Wholesaler profile data for responses"""
    id: str
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


class DistributorProfileData(BaseModel):
    """Distributor profile data for responses"""
    id: str
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


class UserProfileResponse(BaseModel):
    """Complete user profile response"""
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    wholesaler_profile: Optional[WholesalerProfileData] = None
    distributor_profile: Optional[DistributorProfileData] = None


class WholesalerProfileUpdate(BaseModel):
    """Wholesaler profile update fields"""
    business_name: Optional[str] = Field(None, min_length=2, max_length=255)
    business_address: Optional[str] = Field(None, min_length=10, max_length=500)
    business_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    business_email: Optional[EmailStr] = None
    owner_full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    owner_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    owner_email: Optional[EmailStr] = None
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100)
    account_name: Optional[str] = Field(None, min_length=2, max_length=255)
    account_number: Optional[str] = Field(None, min_length=10, max_length=20)


class DistributorProfileUpdate(BaseModel):
    """Distributor profile update fields"""
    business_name: Optional[str] = Field(None, min_length=2, max_length=255)
    business_address: Optional[str] = Field(None, min_length=10, max_length=500)
    business_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    business_email: Optional[EmailStr] = None
    owner_full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    owner_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    owner_email: Optional[EmailStr] = None
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100)
    account_name: Optional[str] = Field(None, min_length=2, max_length=255)
    account_number: Optional[str] = Field(None, min_length=10, max_length=20)


class UserProfileUpdate(BaseModel):
    """User profile update request"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    wholesaler_profile: Optional[WholesalerProfileUpdate] = None
    distributor_profile: Optional[DistributorProfileUpdate] = None
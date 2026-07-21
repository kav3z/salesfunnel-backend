# internal imports 
from app.models.user import UserRole

# external imports
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    """Token response schema with user info"""
    access_token: str
    token_type: str
    user_id: str
    role: UserRole

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "role": "wholesaler"
            }
        }
    )


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., description="Account password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "wholesaler@example.com",
                "password": "Password123!"
            }
        }
    )


class UserResponse(BaseModel):
    """Basic user response schema"""
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "email": "wholesaler@example.com",
                "full_name": "Apex Wholesale Ltd",
                "phone": "+2348012345678",
                "role": "wholesaler",
                "is_active": True
            }
        }
    )


class WholesalerProfileData(BaseModel):
    """Wholesaler profile data for responses"""
    id: str
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
    has_submitted_documents: bool = False
    is_verified: bool
    cac_certificate_url: Optional[str] = None
    tin_certificate_url: Optional[str] = None
    utility_bill_url: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "34dc8ca4-e353-416b-b5b0-643c25aa15b8",
                "business_name": "Apex Wholesale Ltd",
                "cac_registration_number": "RC123456",
                "business_address": "12 Commercial Avenue, Ikeja, Lagos",
                "business_phone": "+2348012345678",
                "business_email": "wholesaler@example.com",
                "tin": "TIN987654321",
                "owner_full_name": "John Doe",
                "owner_phone": "+2348012345678",
                "owner_email": "johndoe@example.com",
                "bank_name": "Access Bank",
                "account_name": "Apex Wholesale Ltd",
                "account_number": "0123456789",
                "has_submitted_documents": True,
                "is_verified": True,
                "cac_certificate_url": "/uploads/wholesaler/cac_certificate.pdf",
                "tin_certificate_url": "/uploads/wholesaler/tin_certificate.pdf",
                "utility_bill_url": "/uploads/wholesaler/utility_bill.pdf"
            }
        }
    )


class DistributorProfileData(BaseModel):
    """Distributor profile data for responses"""
    id: str
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
    has_submitted_documents: bool = False
    is_verified: bool
    cac_certificate_url: Optional[str] = None
    tin_certificate_url: Optional[str] = None
    utility_bill_url: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                "business_name": "Prime Distribution Hub",
                "cac_registration_number": "RC654321",
                "business_address": "45 Warehouse Road, Apapa, Lagos",
                "business_phone": "+2348098765432",
                "business_email": "distributor@example.com",
                "tin": "TIN123456789",
                "owner_full_name": "Jane Smith",
                "owner_phone": "+2348098765432",
                "owner_email": "janesmith@example.com",
                "bank_name": "Zenith Bank",
                "account_name": "Prime Distribution Hub",
                "account_number": "9876543210",
                "has_submitted_documents": True,
                "is_verified": True,
                "cac_certificate_url": "/uploads/distributor/cac_certificate.pdf",
                "tin_certificate_url": "/uploads/distributor/tin_certificate.pdf",
                "utility_bill_url": "/uploads/distributor/utility_bill.pdf"
            }
        }
    )


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "email": "wholesaler@example.com",
                "full_name": "Apex Wholesale Ltd",
                "phone": "+2348012345678",
                "role": "wholesaler",
                "is_active": True,
                "created_at": "2026-01-15T10:30:00Z",
                "updated_at": "2026-07-19T14:00:00Z",
                "wholesaler_profile": {
                    "id": "34dc8ca4-e353-416b-b5b0-643c25aa15b8",
                    "business_name": "Apex Wholesale Ltd",
                    "business_address": "12 Commercial Avenue, Ikeja, Lagos",
                    "business_phone": "+2348012345678",
                    "business_email": "wholesaler@example.com",
                    "is_verified": True
                }
            }
        }
    )


class WholesalerProfileUpdate(BaseModel):
    """Wholesaler profile update fields"""
    business_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Updated Business Name")
    business_address: Optional[str] = Field(None, min_length=10, max_length=500, description="Updated Business Address")
    business_phone: Optional[str] = Field(None, min_length=10, max_length=20, description="Updated Business Phone Number")
    business_email: Optional[EmailStr] = Field(None, description="Updated Business Email")
    owner_full_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Updated Owner Full Name")
    owner_phone: Optional[str] = Field(None, min_length=10, max_length=20, description="Updated Owner Phone Number")
    owner_email: Optional[EmailStr] = Field(None, description="Updated Owner Email")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "business_name": "Apex Wholesale Global Ltd",
                "business_address": "15 Commercial Avenue, Ikeja, Lagos",
                "business_phone": "+2348012345699",
                "business_email": "info@apexwholesale.com"
            }
        }
    )


class DistributorProfileUpdate(BaseModel):
    """Distributor profile update fields"""
    business_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Updated Business Name")
    business_address: Optional[str] = Field(None, min_length=10, max_length=500, description="Updated Business Address")
    business_phone: Optional[str] = Field(None, min_length=10, max_length=20, description="Updated Business Phone Number")
    business_email: Optional[EmailStr] = Field(None, description="Updated Business Email")
    owner_full_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Updated Owner Full Name")
    owner_phone: Optional[str] = Field(None, min_length=10, max_length=20, description="Updated Owner Phone Number")
    owner_email: Optional[EmailStr] = Field(None, description="Updated Owner Email")
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Updated Bank Name")
    account_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Updated Account Name")
    account_number: Optional[str] = Field(None, min_length=10, max_length=20, description="Updated Account Number")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "business_name": "Prime Logistics & Distribution",
                "business_address": "50 Warehouse Road, Apapa, Lagos",
                "business_phone": "+2348098765400",
                "business_email": "contact@primedistribution.com"
            }
        }
    )


class UserProfileUpdate(BaseModel):
    """User profile update request"""
    wholesaler_profile: Optional[WholesalerProfileUpdate] = None
    distributor_profile: Optional[DistributorProfileUpdate] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wholesaler_profile": {
                    "business_name": "Apex Wholesale Global Ltd",
                    "business_address": "15 Commercial Avenue, Ikeja, Lagos",
                    "business_phone": "+2348012345699",
                    "business_email": "info@apexwholesale.com",
                    "owner_full_name": "John Doe",
                    "owner_phone": "+2348012345678",
                    "owner_email": "founder@apexwholesale.com"
                }
            }
        }
    )
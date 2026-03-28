from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from uuid import uuid4, UUID
from datetime import datetime

if TYPE_CHECKING:
    from app.models.user import User


class DistributorProfile(SQLModel, table=True):
    __tablename__ = "distributor_profiles" #type: ignore
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    
    # Company Information
    business_name: str = Field(..., max_length=255)
    cac_registration_number: str = Field(..., max_length=50, unique=True)
    business_address: str = Field(..., max_length=500)
    business_phone: str = Field(..., max_length=20)
    business_email: str = Field(..., max_length=255)
    
    # Tax & Compliance
    tin: str = Field(..., max_length=50, unique=True)
    
    # Owner/Director Details
    owner_full_name: str = Field(..., max_length=255)
    owner_phone: str = Field(..., max_length=20)
    owner_email: str = Field(..., max_length=255)
    
    # Bank Details (for payment settlement)
    bank_name: str = Field(..., max_length=100)
    account_name: str = Field(..., max_length=255)
    account_number: str = Field(..., max_length=20)

    # paystack information
    subaccount_code: str = Field(nullable=True)
    
    # Verification Documents (file paths/URLs)
    cac_certificate_url: Optional[str] = Field(default=None, max_length=500)
    tin_certificate_url: Optional[str] = Field(default=None, max_length=500)
    utility_bill_url: Optional[str] = Field(default=None, max_length=500)
    
    # Verification status
    is_verified: bool = Field(default=False)
    verified_at: Optional[datetime] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    user: Optional["User"] = Relationship(back_populates="distributor_profile")

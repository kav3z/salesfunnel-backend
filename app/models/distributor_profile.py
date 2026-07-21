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
    cac_registration_number: Optional[str] = Field(default=None, max_length=50, unique=True, nullable=True)
    business_address: str = Field(..., max_length=500)
    business_phone: str = Field(..., max_length=20)
    business_email: str = Field(..., max_length=255)
    
    # Tax & Compliance
    tin: Optional[str] = Field(default=None, max_length=50, unique=True, nullable=True)
    
    # Owner/Director Details
    owner_full_name: Optional[str] = Field(default=None, max_length=255, nullable=True)
    owner_phone: Optional[str] = Field(default=None, max_length=20, nullable=True)
    owner_email: Optional[str] = Field(default=None, max_length=255, nullable=True)
    
    # Bank Details (for payment settlement)
    bank_name: Optional[str] = Field(default=None, max_length=100, nullable=True)
    account_name: Optional[str] = Field(default=None, max_length=255, nullable=True)
    account_number: Optional[str] = Field(default=None, max_length=20, nullable=True)

    # paystack information
    subaccount_code: Optional[str] = Field(default=None, nullable=True)
    paystack_dedicated_account_id: Optional[str] = Field(default=None, nullable=True)
    is_bank_active: bool = Field(default=False)
    
    # Verification Documents (file paths/URLs)
    cac_certificate_url: Optional[str] = Field(default=None, max_length=500)
    tin_certificate_url: Optional[str] = Field(default=None, max_length=500)
    utility_bill_url: Optional[str] = Field(default=None, max_length=500)
    
    # Verification status
    has_submitted_documents: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    verified_at: Optional[datetime] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    user: Optional["User"] = Relationship(back_populates="distributor_profile")

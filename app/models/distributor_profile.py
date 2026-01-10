from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from .user import User


class DistributorProfile(SQLModel, table=True):
    __tablename__ = "distributor_profiles" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        unique=True,
        index=True
    )
    
    # Business information
    company_name: str = Field(nullable=False)
    business_address: str = Field(nullable=False)
    business_registration_number: Optional[str] = Field(default=None)
    
    # Bank account details
    bank_name: Optional[str] = Field(default=None)
    account_number: Optional[str] = Field(default=None)
    account_name: Optional[str] = Field(default=None)
    
    # Operating details
    operating_hours: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    delivery_zones: Optional[list] = Field(default=None, sa_column=Column(JSON))
    
    # Performance metrics
    avg_fulfillment_time_minutes: Optional[int] = Field(default=None)
    total_orders_fulfilled: int = Field(default=0)
    rating: Optional[Decimal] = Field(
        default=None,
        decimal_places=2,
        max_digits=3
    )
    
    # Status
    is_verified: bool = Field(default=False)
    
    # Relationships
    user: "User" = Relationship(back_populates="distributor_profile")

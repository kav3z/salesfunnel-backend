from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from .user import User


class WholesalerProfile(SQLModel, table=True):
    __tablename__ = "wholesaler_profiles" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        unique=True,
        index=True
    )
    
    # Business information
    business_name: str = Field(nullable=False)
    business_address: str = Field(nullable=False)
    business_registration_number: Optional[str] = Field(default=None)
    tax_id: Optional[str] = Field(default=None)
    
    # Credit information
    credit_limit: Optional[Decimal] = Field(
        default=None,
        decimal_places=2,
        max_digits=10
    )
    credit_used: Decimal = Field(
        default=0,
        decimal_places=2,
        max_digits=10
    )
    credit_status: Optional[str] = Field(default="good")
    
    # Order statistics
    total_orders_placed: int = Field(default=0)
    total_amount_spent: Decimal = Field(
        default=0,
        decimal_places=2,
        max_digits=12
    )
    
    # Status
    is_verified: bool = Field(default=False)
    
    # Relationships
    user: "User" = Relationship(back_populates="wholesaler_profile")

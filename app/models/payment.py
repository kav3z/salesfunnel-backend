from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from .order import Order
    from .user import User


class PaymentStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"


class Payment(SQLModel, table=True):
    __tablename__ = "payments" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(
        foreign_key="orders.id",
        nullable=False,
        unique=True,
        index=True
    )
    reference_number: str = Field(unique=True, index=True, nullable=False)
    amount: Decimal = Field(
        nullable=False,
        decimal_places=2,
        max_digits=10
    )
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.BANK_TRANSFER,
        nullable=False
    )
    bank_details: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    proof_image_url: Optional[str] = Field(default=None)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, nullable=False, index=True)
    rejection_reason: Optional[str] = Field(default=None)
    
    # Timestamps
    initiated_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)
    rejected_at: Optional[datetime] = Field(default=None)
    
    # Verified by
    verified_by_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.id"
    )
    
    # Relationships
    order: "Order" = Relationship(back_populates="payment")
    verified_by: Optional["User"] = Relationship(back_populates="payments_verified")

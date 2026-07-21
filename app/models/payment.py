from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from .order import Order
    from .user import User
    from .distributor_profile import DistributorProfile


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"



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
    distributor_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )
    reference_number: str = Field(unique=True, index=True, nullable=False)
    amount: Decimal = Field(
        nullable=False,
        decimal_places=2,
        max_digits=16
    )
    payment_method: str = Field(
        nullable=False
    )
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, nullable=False, index=True)
    order_number: str = Field(nullable=False)
    wholesaler_name: str = Field(nullable=False)
    
    # Timestamps
    initiated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    order: "Order" = Relationship(back_populates="payment")
    distributor: "User" = Relationship(back_populates="payments")

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from .user import User
    from .order_item import OrderItem
    from .payment import Payment


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    APPROVED = "approved"
    READY_FOR_PICKUP = "ready_for_pickup"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(SQLModel, table=True):
    __tablename__ = "orders" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_number: str = Field(unique=True, index=True, nullable=False)
    wholesaler_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    distributor_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    total_amount: Decimal = Field(
        nullable=False,
        decimal_places=2,
        max_digits=10
    )
    status: OrderStatus = Field(default=OrderStatus.PENDING, nullable=False, index=True)
    notes: Optional[str] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)
    ready_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    wholesaler: "User" = Relationship(
        back_populates="orders_as_wholesaler",
        sa_relationship_kwargs={"foreign_keys": "[Order.wholesaler_id]"}
    )
    distributor: "User" = Relationship(
        back_populates="orders_as_distributor",
        sa_relationship_kwargs={"foreign_keys": "[Order.distributor_id]"}
    )
    order_items: list["OrderItem"] = Relationship(back_populates="order", cascade_delete=True)
    payment: Optional["Payment"] = Relationship(back_populates="order")

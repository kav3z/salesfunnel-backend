from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
import uuid

if TYPE_CHECKING:
    from .user import User


class NotificationType(str, Enum):
    ORDER_PLACED = "order_placed"
    PAYMENT_SUBMITTED = "payment_submitted"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_REJECTED = "payment_rejected"
    ORDER_READY = "order_ready"
    ORDER_COMPLETED = "order_completed"
    ORDER_DELAYED = "order_delayed"
    ORDER_CANCELLED = "order_cancelled"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    title: str = Field(nullable=False)
    message: str = Field(nullable=False)
    type: NotificationType = Field(nullable=False)
    
    # Related entities
    related_order_id: Optional[uuid.UUID] = Field(default=None)
    related_payment_id: Optional[uuid.UUID] = Field(default=None)
    
    # Status
    is_read: bool = Field(default=False, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    read_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    user: "User" = Relationship(back_populates="notifications")

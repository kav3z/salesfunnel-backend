# External imports
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

# Local imports
from app.models.user import UserRole
from app.models.order import OrderStatus
from app.models.payment import PaymentStatus


# Admin-specific schemas
class AdminUserResponse(BaseModel):
    """Extended user response for admin view"""
    id: str
    email: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    business_name: Optional[str] = None
    is_verified: Optional[bool] = None
    
    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    """Paginated user list for admin"""
    users: List[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminOrderResponse(BaseModel):
    """Extended order response with payment status for admin view"""
    id: UUID
    order_number: str
    wholesaler_id: UUID
    wholesaler_name: Optional[str]
    distributor_id: UUID
    distributor_name: Optional[str]
    total_amount: Decimal
    status: OrderStatus
    payment_status: Optional[PaymentStatus]
    payment_reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AdminOrderListResponse(BaseModel):
    """Paginated order list for admin"""
    orders: List[AdminOrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderStatusOverride(BaseModel):
    """Schema for admin order status override"""
    status: OrderStatus
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for status override")

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    """Schema for creating an order from cart"""
    notes: Optional[str] = Field(None, max_length=500, description="Optional order notes")
    delivery_address: str | None = None
    is_delivery: bool
    contact_name: str
    contact_phone_no: str


class OrderItemResponse(BaseModel):
    """Schema for order item response"""
    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: UUID
    order_number: str
    wholesaler_id: UUID
    wholesaler_name: str
    distributor_name: str
    total_amount: Decimal
    status: OrderStatus
    notes: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]
    approved_at: Optional[datetime]
    ready_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    """Schema for detailed order response with items"""
    items: List[OrderItemResponse]
    
    class Config: # type: ignore
        from_attributes = True


class OrderListResponse(BaseModel):
    """Schema for paginated order list response"""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    status: OrderStatus

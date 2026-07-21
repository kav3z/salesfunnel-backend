from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    """Schema for creating an order from cart"""
    notes: Optional[str] = Field(None, max_length=500, description="Optional order notes for the distributor")
    delivery_address: Optional[str] = Field(None, description="Delivery address if is_delivery is True")
    is_delivery: bool = Field(..., description="Set True for door delivery, False for pickup")
    contact_name: str = Field(..., description="Recipient contact name")
    contact_phone_no: str = Field(..., description="Recipient contact phone number")
    mode_of_transport: Optional[str] = Field(None, description="Mode of transport e.g. Truck, Van, Motorcycle, Pickup")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notes": "Please handle fragile cases with care",
                "delivery_address": "12 Commercial Avenue, Ikeja, Lagos",
                "is_delivery": True,
                "contact_name": "John Doe",
                "contact_phone_no": "+2348012345678",
                "mode_of_transport": "Truck"
            }
        }
    )


class OrderItemResponse(BaseModel):
    """Schema for order item response"""
    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "e81d71c9-e9e4-49d8-96be-8248f20d5a11",
                "product_id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                "product_name": "Premium Energy Drink (Case of 24)",
                "product_sku": "DRK-ENG-001",
                "quantity": 10,
                "unit_price": "15000.00",
                "subtotal": "150000.00"
            }
        }
    )


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
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    mode_of_transport: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a11d71c9-e9e4-49d8-96be-8248f20d5a22",
                "order_number": "ORD-20260719-001",
                "wholesaler_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "wholesaler_name": "Apex Wholesale Ltd",
                "distributor_name": "Prime Distribution Hub",
                "total_amount": "150000.00",
                "status": "paid",
                "notes": "Handle with care",
                "created_at": "2026-07-19T10:00:00Z",
                "paid_at": "2026-07-19T10:05:00Z",
                "approved_at": None,
                "ready_at": None,
                "completed_at": None,
                "cancelled_at": None,
                "mode_of_transport": "Truck"
            }
        }
    )


class OrderDetailResponse(OrderResponse):
    """Schema for detailed order response with items"""
    items: List[OrderItemResponse]
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a11d71c9-e9e4-49d8-96be-8248f20d5a22",
                "order_number": "ORD-20260719-001",
                "wholesaler_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "wholesaler_name": "Apex Wholesale Ltd",
                "distributor_name": "Prime Distribution Hub",
                "total_amount": "150000.00",
                "status": "paid",
                "notes": "Handle with care",
                "created_at": "2026-07-19T10:00:00Z",
                "paid_at": "2026-07-19T10:05:00Z",
                "items": [
                    {
                        "id": "e81d71c9-e9e4-49d8-96be-8248f20d5a11",
                        "product_id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                        "product_name": "Premium Energy Drink (Case of 24)",
                        "product_sku": "DRK-ENG-001",
                        "quantity": 10,
                        "unit_price": "15000.00",
                        "subtotal": "150000.00"
                    }
                ]
            }
        }
    )


class OrderListResponse(BaseModel):
    """Schema for paginated order list response"""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orders": [
                    {
                        "id": "a11d71c9-e9e4-49d8-96be-8248f20d5a22",
                        "order_number": "ORD-20260719-001",
                        "wholesaler_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                        "wholesaler_name": "Apex Wholesale Ltd",
                        "distributor_name": "Prime Distribution Hub",
                        "total_amount": "150000.00",
                        "status": "paid",
                        "created_at": "2026-07-19T10:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
    )


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    status: OrderStatus = Field(..., description="Target status (e.g. approved, ready_for_pickup, completed, cancelled)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "approved"
            }
        }
    )

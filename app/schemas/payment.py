from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"


class PaymentInfoResponse(BaseModel):
    """Payment information response"""
    order_number: str
    wholesaler_name: str
    amount: Decimal
    date: str
    time: str
    reference_number: str
    status: PaymentStatus


class PaymentListResponse(BaseModel):
    """Paginated payment list response"""
    payments: List[PaymentInfoResponse]
    total: int = Field(..., description="Total number of payments")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")

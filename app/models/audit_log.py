from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON
import uuid
import pytz


def get_lagos_time():
    """Get current time in Lagos timezone without tzinfo"""
    return datetime.now(pytz.timezone('Africa/Lagos')).replace(tzinfo=None)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs" # type: ignore
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Actor
    user_id: Optional[uuid.UUID] = Field(default=None, index=True)
    user_email: Optional[str] = Field(default=None)
    
    # Action details
    action_type: str = Field(nullable=False, index=True)
    entity_type: str = Field(nullable=False, index=True)
    entity_id: Optional[uuid.UUID] = Field(default=None, index=True)
    
    # State tracking
    old_value: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    new_value: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Request details
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    
    # Additional context
    extra_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Timestamp
    timestamp: datetime = Field(default_factory=get_lagos_time, index=True)

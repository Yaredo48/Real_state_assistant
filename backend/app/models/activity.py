"""
Activity logging models for audit trails.
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, INET
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base


class ActivityLog(Base):
    """User activity logging model."""
    
    __tablename__ = "activity_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100))
    resource_type = Column(String(50))
    resource_id = Column(UUID(as_uuid=True))
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
"""
Payment models for transaction processing.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base


class Payment(Base):
    """Payment transaction model."""
    
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    stripe_payment_id = Column(String(255))
    amount = Column(Numeric(10, 2))
    currency = Column(String(3), default="USD")
    status = Column(String(50))  # pending, completed, failed, refunded
    payment_method = Column(String(50))
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="payments")
    report = relationship("Report", back_populates="payment")
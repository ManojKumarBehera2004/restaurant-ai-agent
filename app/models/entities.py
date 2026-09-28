"""
SQLAlchemy Entity Models.
Defines persistent tables for Orders, Support Tickets, Conversation Sessions, and Audit Logs.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class OrderEntity(Base):
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), index=True, nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=True)
    status = Column(String(50), nullable=False, default="RECEIVED")
    items_json = Column(Text, nullable=False)
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, nullable=False)
    delivery_fee = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False)
    delivery_address = Column(String(255), nullable=False)
    delivery_partner = Column(String(100), nullable=True)
    estimated_delivery_minutes = Column(Integer, nullable=True)
    payment_status = Column(String(50), nullable=False, default="PAID")
    can_cancel = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class TicketEntity(Base):
    __tablename__ = "support_tickets"

    id = Column(String(50), primary_key=True, index=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    customer_id = Column(String(50), index=True, nullable=True)
    order_id = Column(String(50), index=True, nullable=True)
    category = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False, default="Medium")
    sentiment = Column(String(50), nullable=False, default="Neutral")
    issue_summary = Column(String(255), nullable=False)
    details = Column(Text, nullable=False)
    resolution_action = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="OPEN")
    created_at = Column(DateTime, default=utc_now)
    resolved_at = Column(DateTime, nullable=True)


class ConversationMessageEntity(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls_json = Column(Text, nullable=True)
    rag_sources_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utc_now)


class AuditLogEntity(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), index=True, nullable=False)
    session_id = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utc_now)

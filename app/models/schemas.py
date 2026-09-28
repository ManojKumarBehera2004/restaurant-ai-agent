"""
Pydantic Validation & Serialization Schemas.
Enforces strict typing for tool parameters, API endpoints, agent responses, and workflows.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ---------------------------------------------------------
# Order Schemas
# ---------------------------------------------------------

class OrderItemSchema(BaseModel):
    name: str = Field(..., description="Name of the food item")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    unit_price: float = Field(..., ge=0, description="Price per unit")
    special_instructions: Optional[str] = Field(None, description="Specific instructions like extra spicy")


class OrderResponse(BaseModel):
    id: str = Field(..., description="Unique order identifier (e.g. ORD-1001)")
    customer_id: str
    customer_name: str
    status: str = Field(..., description="Current status: RECEIVED, PREPARING, OUT_FOR_DELIVERY, DELIVERED, CANCELLED, FAILED")
    items: List[OrderItemSchema]
    subtotal: float
    tax: float
    delivery_fee: float
    total: float
    delivery_address: str
    delivery_partner: Optional[str] = None
    estimated_delivery_minutes: Optional[int] = None
    payment_status: str
    can_cancel: bool
    created_at: datetime
    updated_at: datetime


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    estimated_delivery_minutes: Optional[int] = None
    delivery_partner: Optional[str] = None
    last_updated: datetime
    message: str


# ---------------------------------------------------------
# Support Ticket Schemas
# ---------------------------------------------------------

class TicketCreateRequest(BaseModel):
    category: str = Field(
        ...,
        description="Category: Payment, Order, Delivery, Refund, Technical, Other"
    )
    priority: str = Field(
        default="Medium",
        description="Priority level: Low, Medium, High, Critical"
    )
    sentiment: str = Field(
        default="Neutral",
        description="Sentiment: Positive, Neutral, Frustrated, Angry, Urgent"
    )
    issue_summary: str = Field(..., min_length=5, max_length=255, description="Short summary of the issue")
    details: str = Field(..., min_length=5, description="Full explanation of customer complaint")
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    resolution_action: Optional[str] = None


class TicketResponse(BaseModel):
    id: str
    category: str
    priority: str
    sentiment: str
    issue_summary: str
    details: str
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    resolution_action: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------
# Complaint Classification & Automation Workflow Schemas
# ---------------------------------------------------------

class ComplaintClassificationResult(BaseModel):
    category: str = Field(
        ...,
        description="Must be one of: Payment, Order, Delivery, Refund, Technical, Other"
    )
    sentiment: str = Field(
        ...,
        description="Must be one of: Positive, Neutral, Frustrated, Angry, Urgent"
    )
    urgency: str = Field(
        ...,
        description="Assessed urgency: Low, Medium, High, Critical"
    )
    confidence_score: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Classification confidence"
    )
    reasoning: str = Field(
        ...,
        description="Short rationale explaining the classification and urgency"
    )
    suggested_action: str = Field(
        ...,
        description="Recommended operational next step"
    )
    extracted_order_id: Optional[str] = Field(
        None,
        description="Extracted order ID if mentioned in the complaint"
    )


# ---------------------------------------------------------
# Agent Chat & Observability Schemas
# ---------------------------------------------------------

class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


class RAGSourceDoc(BaseModel):
    title: str
    content: str
    similarity_score: float
    source_file: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Customer message")
    session_id: str = Field(default="default_session", description="Session identifier for multi-turn conversation")
    customer_id: Optional[str] = Field(default="CUST-001", description="Authenticated customer ID")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls: List[ToolCallRecord] = []
    rag_sources: List[RAGSourceDoc] = []
    security_flag: bool = False
    intent: Optional[str] = None
    execution_time_ms: float = 0.0
    token_usage_estimate: int = 0
    created_ticket: Optional[TicketResponse] = None


# ---------------------------------------------------------
# System & Diagnostic Schemas
# ---------------------------------------------------------

class DiagnosticToggleRequest(BaseModel):
    simulate_order_service_outage: Optional[bool] = None
    simulate_llm_timeout: Optional[bool] = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    llm_provider: str
    llm_model: str
    vector_store_status: str
    database_status: str
    order_outage_simulation_active: bool

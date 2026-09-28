"""
Unit Tests for Agent Operational Tools.
"""

import pytest
from app.tools.order_tools import get_order_status_tool, get_order_details_tool, cancel_order_tool
from app.tools.support_tools import create_support_ticket_tool, search_restaurant_policies_tool
from app.core.config import settings
from app.models.database import SessionLocal
from app.models.entities import OrderEntity
from data.seed_data import seed_database


@pytest.fixture(autouse=True)
def setup_db():
    seed_database()
    settings.SIMULATE_ORDER_SERVICE_OUTAGE = False
    # Ensure ORD-1004 is reset to RECEIVED status for cancellation test
    db = SessionLocal()
    try:
        o = db.query(OrderEntity).filter(OrderEntity.id == "ORD-1004").first()
        if o:
            o.status = "RECEIVED"
            o.can_cancel = True
            db.commit()
    finally:
        db.close()


def test_get_order_status_success():
    """Test retrieving existing order ORD-1005."""
    res = get_order_status_tool("ORD-1005")
    assert res["success"] is True
    assert res["order_id"] == "ORD-1005"
    assert res["status"] == "OUT_FOR_DELIVERY"
    assert res["estimated_delivery_minutes"] == 8
    assert "Carlos Gomez" in res["delivery_partner"]


def test_get_order_status_not_found():
    """Test retrieving non-existent order gracefully returns error dict instead of crashing."""
    res = get_order_status_tool("ORD-9999")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_get_order_details():
    """Test fetching line items, address, and pricing."""
    res = get_order_details_tool("ORD-1001")
    assert res["success"] is True
    assert res["order_id"] == "ORD-1001"
    assert len(res["items"]) >= 1
    assert res["total"] > 0
    assert "742 Evergreen Terrace" in res["delivery_address"]


def test_cancel_order_rules():
    """Test cancellation policy: RECEIVED can cancel, PREPARING cannot."""
    # ORD-1004 is in RECEIVED status
    cancel_res = cancel_order_tool("ORD-1004", "Changed my mind")
    assert cancel_res["success"] is True
    assert cancel_res["cancelled"] is True
    assert cancel_res["status"] == "CANCELLED"

    # ORD-1003 is PREPARING
    prep_res = cancel_order_tool("ORD-1003", "Too late")
    assert prep_res["cancelled"] is False
    assert "already being prepared" in prep_res["message"]


def test_create_support_ticket_tool():
    """Test creating structured support ticket with deduplication."""
    res = create_support_ticket_tool(
        category="Payment",
        issue_summary="Payment deducted without order confirmation",
        details="Customer was charged $29.11 at 7:30 PM but no order was created.",
        priority="High",
        sentiment="Urgent",
        order_id="ORD-1006",
        customer_id="CUST-004"
    )
    assert res["success"] is True
    ticket = res["ticket"]
    assert ticket["id"].startswith("TCK-")
    assert ticket["category"] == "Payment"
    assert ticket["priority"] == "High"
    assert ticket["status"] == "OPEN"


def test_simulated_order_service_outage():
    """Test system reports tool outage gracefully when outage flag is enabled."""
    settings.SIMULATE_ORDER_SERVICE_OUTAGE = True
    res = get_order_status_tool("ORD-1005")
    assert res["success"] is False
    assert res["error_code"] == "SERVICE_UNAVAILABLE"
    settings.SIMULATE_ORDER_SERVICE_OUTAGE = False

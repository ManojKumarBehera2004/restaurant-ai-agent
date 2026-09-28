"""
Unit Tests for Complaint Classification & End-to-End Automation Workflow.
"""

import pytest
from app.workflows.classifier import ComplaintClassifier
from app.workflows.complaint_workflow import ComplaintWorkflow
from data.seed_data import seed_database


@pytest.fixture(autouse=True)
def setup_db():
    seed_database()


def test_classifier_payment_issue():
    """Test classification of payment failure complaint."""
    text = "My payment was deducted from my debit card but the order failed on the checkout screen."
    result = ComplaintClassifier.classify(text)
    assert result.category == "Payment"
    assert result.urgency in ["High", "Critical"]
    assert "suggested_action" in result.model_dump()


def test_classifier_delivery_delay():
    """Test classification of courier delivery complaint."""
    text = "My delivery is 40 minutes late and the driver is not answering calls."
    result = ComplaintClassifier.classify(text)
    assert result.category == "Delivery"
    assert result.urgency in ["Medium", "High"]


def test_classifier_allergy_safety_critical():
    """Test safety emergency triggers Critical urgency."""
    text = "Severe emergency! The burger contained peanuts and my child has a life threatening peanut allergy."
    result = ComplaintClassifier.classify(text)
    assert result.urgency == "Critical"
    assert "safety" in result.reasoning.lower() or "health" in result.reasoning.lower()


def test_end_to_end_complaint_workflow():
    """Test end-to-end complaint triage, ticket creation, and persistence."""
    complaint = "Charged twice for order ORD-1006 and bank account shows duplicate deduction."
    trace = ComplaintWorkflow.process_complaint(
        complaint_text=complaint,
        customer_id="CUST-004",
        order_id="ORD-1006"
    )

    assert trace["success"] is True
    assert trace["ticket"] is not None
    assert trace["ticket"]["id"].startswith("TCK-")
    assert trace["ticket"]["category"] == "Payment"
    assert trace["ticket"]["order_id"] == "ORD-1006"
    assert trace["ticket"]["status"] == "OPEN"

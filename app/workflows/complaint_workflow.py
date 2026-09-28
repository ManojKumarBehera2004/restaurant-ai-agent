"""
End-to-End Automation Workflow: Customer Complaint Triage & Escalation.
Pipeline: Complaint -> Classification -> Sentiment/Urgency -> Structured Ticket -> Notification -> Audit.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.workflows.classifier import ComplaintClassifier
from app.models.schemas import TicketCreateRequest, ComplaintClassificationResult
from app.services.ticket_service import ticket_service
from app.core.logging import logger, log_agent_event


class ComplaintWorkflow:
    """Executes the automated complaint triage and ticket creation pipeline."""

    @classmethod
    def process_complaint(
        cls,
        complaint_text: str,
        customer_id: Optional[str] = "CUST-001",
        order_id: Optional[str] = None,
        llm_service=None
    ) -> Dict[str, Any]:
        """
        Execute end-to-end complaint workflow:
        1. Classify category, sentiment, urgency
        2. Validate structured schema
        3. Create persisted support ticket with deduplication
        4. Trigger notification dispatch
        5. Return comprehensive execution trace
        """
        # Step 1: AI Classification & Urgency Assessment
        classification: ComplaintClassificationResult = ComplaintClassifier.classify(
            complaint_text=complaint_text,
            llm_service=llm_service
        )

        effective_order_id = order_id or classification.extracted_order_id

        # Step 2: Build Structured Ticket Request
        issue_summary = f"[{classification.category}] {complaint_text[:60].strip()}..."
        ticket_data = TicketCreateRequest(
            category=classification.category,
            priority=classification.urgency,
            sentiment=classification.sentiment,
            issue_summary=issue_summary,
            details=complaint_text,
            customer_id=customer_id,
            order_id=effective_order_id,
            resolution_action=classification.suggested_action
        )

        # Step 3: Idempotent Ticket Persistence
        idempotency_key = f"wf-{customer_id}-{effective_order_id or 'none'}-{classification.category}-{hash(complaint_text)}"
        ticket_result = ticket_service.create_ticket(ticket_data, idempotency_key=idempotency_key)

        # Step 4: Record Workflow Trace
        workflow_trace = {
            "workflow_name": "ComplaintTriagePipeline",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": customer_id,
            "order_id": effective_order_id,
            "classification": classification.model_dump(),
            "ticket": ticket_result.get("ticket"),
            "success": ticket_result.get("success", False)
        }

        log_agent_event(
            "COMPLAINT_WORKFLOW_COMPLETED",
            f"Complaint triage workflow completed for ticket {ticket_result.get('ticket', {}).get('id', 'N/A')}",
            workflow_trace
        )

        return workflow_trace

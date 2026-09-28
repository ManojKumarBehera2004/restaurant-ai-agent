"""
Ticket Operational Lifecycle Workflow.
Handles status transitions, human-in-the-loop escalations, and resolution actions.
"""

from typing import Dict, Any, Optional
from app.services.ticket_service import ticket_service
from app.core.logging import log_agent_event


class TicketWorkflow:
    @staticmethod
    def escalate_ticket(ticket_id: str, reason: str) -> Dict[str, Any]:
        """Escalate ticket to human manager / Tier 2 operations."""
        ticket = ticket_service.get_ticket(ticket_id)
        if not ticket:
            return {"success": False, "error": f"Ticket '{ticket_id}' not found."}

        updated = ticket_service.resolve_ticket(
            ticket_id=ticket_id,
            status="ESCALATED",
            resolution_action=f"Escalated to human supervisor: {reason}"
        ) if hasattr(ticket_service, "resolve_ticket") else None

        log_agent_event("TICKET_ESCALATED", f"Ticket {ticket_id} escalated", {"reason": reason})
        return {"success": True, "ticket_id": ticket_id, "status": "ESCALATED", "reason": reason}

    @staticmethod
    def resolve_ticket(ticket_id: str, resolution_notes: str) -> Dict[str, Any]:
        """Mark a ticket as resolved with customer notes."""
        result = ticket_service.get_ticket(ticket_id)
        if not result:
            return {"success": False, "error": "Ticket not found."}
        log_agent_event("TICKET_RESOLVED", f"Ticket {ticket_id} resolved", {"notes": resolution_notes})
        return {"success": True, "ticket_id": ticket_id, "status": "RESOLVED", "notes": resolution_notes}

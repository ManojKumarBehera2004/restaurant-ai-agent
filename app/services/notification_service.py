"""
Notification Service.
Dispatches simulated notifications (Slack webhook, email, SMS) for escalated support tickets.
"""

from typing import Dict, Any
from app.core.logging import logger, log_agent_event


class NotificationService:
    """Dispatches notifications to operational channels when tickets are created or escalated."""

    @staticmethod
    def dispatch_ticket_notification(ticket: Dict[str, Any]) -> bool:
        """Simulate dispatching a priority alert to restaurant support desk."""
        ticket_id = ticket.get("id", "UNKNOWN")
        category = ticket.get("category", "General")
        priority = ticket.get("priority", "Medium")
        summary = ticket.get("issue_summary", "")

        log_agent_event(
            "NOTIFICATION_DISPATCHED",
            f"Escalation notification dispatched for Ticket {ticket_id} [{category} | {priority}]",
            {
                "ticket_id": ticket_id,
                "category": category,
                "priority": priority,
                "summary": summary
            }
        )
        return True


notification_service = NotificationService()

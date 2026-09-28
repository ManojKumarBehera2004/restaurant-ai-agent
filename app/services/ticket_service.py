"""
Ticket Business Service.
Handles support ticket lifecycle, validation, idempotency, and notifications.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.schemas import TicketCreateRequest, TicketResponse
from app.repositories.ticket_repository import TicketRepository
from app.services.notification_service import notification_service
from app.core.logging import logger, log_agent_event


class TicketService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_session(self) -> Session:
        return self.db if self.db else SessionLocal()

    def create_ticket(
        self,
        ticket_data: TicketCreateRequest,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new support ticket and trigger notifications."""
        session = self._get_session()
        try:
            repo = TicketRepository(session)
            ticket_entity = repo.create_ticket(ticket_data, idempotency_key)

            ticket_dict = {
                "id": ticket_entity.id,
                "category": ticket_entity.category,
                "priority": ticket_entity.priority,
                "sentiment": ticket_entity.sentiment,
                "issue_summary": ticket_entity.issue_summary,
                "details": ticket_entity.details,
                "customer_id": ticket_entity.customer_id,
                "order_id": ticket_entity.order_id,
                "resolution_action": ticket_entity.resolution_action,
                "status": ticket_entity.status,
                "created_at": ticket_entity.created_at.isoformat() if ticket_entity.created_at else None,
                "resolved_at": ticket_entity.resolved_at.isoformat() if ticket_entity.resolved_at else None
            }

            # Send notification if High/Critical priority or Payment/Refund issue
            if ticket_entity.priority in ["High", "Critical"] or ticket_entity.category in ["Payment", "Refund"]:
                notification_service.dispatch_ticket_notification(ticket_dict)

            log_agent_event(
                "TICKET_CREATED",
                f"Support ticket {ticket_entity.id} created successfully.",
                ticket_dict
            )

            return {"success": True, "ticket": ticket_dict}
        except Exception as e:
            logger.error(f"Failed to create support ticket: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if not self.db:
                session.close()

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve ticket details."""
        session = self._get_session()
        try:
            repo = TicketRepository(session)
            ticket = repo.get_by_id(ticket_id)
            if not ticket:
                return None
            return {
                "id": ticket.id,
                "category": ticket.category,
                "priority": ticket.priority,
                "sentiment": ticket.sentiment,
                "issue_summary": ticket.issue_summary,
                "details": ticket.details,
                "customer_id": ticket.customer_id,
                "order_id": ticket.order_id,
                "resolution_action": ticket.resolution_action,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None
            }
        finally:
            if not self.db:
                session.close()

    def list_tickets(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List tickets with optional filtering."""
        session = self._get_session()
        try:
            repo = TicketRepository(session)
            tickets = repo.list_tickets(status, category, limit)
            return [
                {
                    "id": t.id,
                    "category": t.category,
                    "priority": t.priority,
                    "sentiment": t.sentiment,
                    "issue_summary": t.issue_summary,
                    "details": t.details,
                    "customer_id": t.customer_id,
                    "order_id": t.order_id,
                    "resolution_action": t.resolution_action,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None
                }
                for t in tickets
            ]
        finally:
            if not self.db:
                session.close()


ticket_service = TicketService()

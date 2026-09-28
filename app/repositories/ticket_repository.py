"""
Support Ticket Repository.
Handles ticket persistence, deduplication via idempotency keys, and listing.
"""

from typing import Optional, List
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from app.models.entities import TicketEntity
from app.models.schemas import TicketCreateRequest


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def generate_ticket_id(self) -> str:
        """Generate human-friendly ticket ID: TCK-YYYYMMDD-XXXX."""
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        short_hex = uuid.uuid4().hex[:4].upper()
        return f"TCK-{now_str}-{short_hex}"

    def create_ticket(
        self,
        ticket_data: TicketCreateRequest,
        idempotency_key: Optional[str] = None
    ) -> TicketEntity:
        """
        Create and persist a new support ticket.
        If idempotency_key is provided and already exists, returns existing ticket to avoid duplicates.
        """
        if idempotency_key:
            existing = self.db.query(TicketEntity).filter(
                TicketEntity.idempotency_key == idempotency_key
            ).first()
            if existing:
                return existing

        ticket_id = self.generate_ticket_id()
        ticket = TicketEntity(
            id=ticket_id,
            idempotency_key=idempotency_key,
            customer_id=ticket_data.customer_id,
            order_id=ticket_data.order_id,
            category=ticket_data.category,
            priority=ticket_data.priority,
            sentiment=ticket_data.sentiment,
            issue_summary=ticket_data.issue_summary,
            details=ticket_data.details,
            resolution_action=ticket_data.resolution_action or "Ticket opened for support triage",
            status="OPEN",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def get_by_id(self, ticket_id: str) -> Optional[TicketEntity]:
        """Fetch ticket by ID."""
        return self.db.query(TicketEntity).filter(TicketEntity.id == ticket_id).first()

    def list_tickets(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[TicketEntity]:
        """List tickets with optional filters."""
        query = self.db.query(TicketEntity)
        if status:
            query = query.filter(TicketEntity.status == status)
        if category:
            query = query.filter(TicketEntity.category == category)
        return query.order_by(TicketEntity.created_at.desc()).limit(limit).all()

    def update_status(
        self,
        ticket_id: str,
        status: str,
        resolution_action: Optional[str] = None
    ) -> Optional[TicketEntity]:
        """Update ticket status and optional resolution note."""
        ticket = self.get_by_id(ticket_id)
        if not ticket:
            return None
        ticket.status = status
        if resolution_action:
            ticket.resolution_action = resolution_action
        if status == "RESOLVED":
            ticket.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

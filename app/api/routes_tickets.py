"""
Support Tickets and Automation Workflow API Endpoints.
Matches Section 3 and Section 2.D of assessment specification.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import TicketCreateRequest, TicketResponse, ComplaintClassificationResult
from app.services.ticket_service import ticket_service
from app.workflows.complaint_workflow import ComplaintWorkflow
from app.workflows.classifier import ComplaintClassifier

router = APIRouter(prefix="/api/support", tags=["Support Tickets"])


@router.post("/tickets", status_code=201)
async def create_support_ticket(req: TicketCreateRequest):
    """Create a support ticket manually or via external automation."""
    result = ticket_service.create_ticket(req)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create ticket"))
    return result.get("ticket")


@router.get("/tickets")
async def list_support_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
):
    """List all support tickets with optional status/category filters."""
    return ticket_service.list_tickets(status=status, category=category, limit=limit)


@router.get("/tickets/{ticket_id}")
async def get_ticket_details(ticket_id: str):
    """Retrieve details for a single support ticket."""
    ticket = ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return ticket


@router.post("/workflow/classify", response_model=ComplaintClassificationResult)
async def test_classify_complaint(complaint_text: str):
    """Direct API endpoint to test the AI complaint classification and triage logic."""
    return ComplaintClassifier.classify(complaint_text)

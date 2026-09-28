"""
Support & Policy Tools for Agent Execution.
"""

from typing import Dict, Any, Optional
from app.models.schemas import TicketCreateRequest
from app.services.ticket_service import ticket_service
from app.rag.retriever import retriever
from app.core.logging import log_agent_event


def create_support_ticket_tool(
    category: str,
    issue_summary: str,
    details: str,
    priority: str = "Medium",
    sentiment: str = "Neutral",
    order_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    resolution_action: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an official support ticket for complex issues, complaints, refunds, or service failures.
    Arguments:
        category: Payment, Order, Delivery, Refund, Technical, or Other
        issue_summary: Brief title of the issue
        details: Comprehensive explanation of the problem
        priority: Low, Medium, High, or Critical
        sentiment: Positive, Neutral, Frustrated, Angry, Urgent
        order_id: Related order ID (if any)
        customer_id: Customer ID (if known)
        resolution_action: Immediate recommended triage action
    """
    try:
        # Validate allowed categories
        allowed_categories = ["Payment", "Order", "Delivery", "Refund", "Technical", "Other"]
        valid_category = category if category in allowed_categories else "Other"

        allowed_priorities = ["Low", "Medium", "High", "Critical"]
        valid_priority = priority if priority in allowed_priorities else "Medium"

        allowed_sentiments = ["Positive", "Neutral", "Frustrated", "Angry", "Urgent"]
        valid_sentiment = sentiment if sentiment in allowed_sentiments else "Neutral"

        ticket_data = TicketCreateRequest(
            category=valid_category,
            priority=valid_priority,
            sentiment=valid_sentiment,
            issue_summary=issue_summary,
            details=details,
            order_id=order_id,
            customer_id=customer_id or "CUST-001",
            resolution_action=resolution_action
        )

        # Generate idempotency key based on order_id and category or issue summary
        idempotency_key = f"{customer_id or 'anon'}-{order_id or 'no-order'}-{valid_category}-{issue_summary[:20]}"
        result = ticket_service.create_ticket(ticket_data, idempotency_key=idempotency_key)
        log_agent_event("TOOL_EXECUTION_SUCCESS", "create_support_ticket executed", {"ticket": result})
        return result
    except Exception as e:
        log_agent_event("TOOL_EXECUTION_ERROR", f"create_support_ticket failed: {str(e)}")
        return {
            "success": False,
            "error_code": "TICKET_CREATION_FAILED",
            "error": f"Failed to generate support ticket: {str(e)}"
        }


def search_restaurant_policies_tool(query: str) -> Dict[str, Any]:
    """
    Search restaurant knowledge base for official policies, FAQs, operating hours, delivery rules, and cancellation terms.
    Arguments:
        query: Specific policy question (e.g. 'refund policy after kitchen starts cooking')
    """
    try:
        docs = retriever.search(query)
        if not docs:
            return {
                "success": True,
                "found": False,
                "message": "No official documented policy was found for this specific query."
            }
        return {
            "success": True,
            "found": True,
            "policies": [
                {
                    "title": d.title,
                    "content": d.content,
                    "similarity_score": d.similarity_score,
                    "source": d.source_file
                }
                for d in docs
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error_code": "RAG_SEARCH_FAILED",
            "error": f"Policy search temporarily unavailable: {str(e)}"
        }

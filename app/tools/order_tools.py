"""
Order Management Tools for Agent Execution.
"""

from typing import Dict, Any
from app.services.order_service import order_service
from app.core.exceptions import AppBaseException
from app.core.logging import log_agent_event


def get_order_status_tool(order_id: str) -> Dict[str, Any]:
    """
    Retrieve authoritative real-time order status, ETA, and courier info from operational database.
    Arguments:
        order_id: The unique identifier of the order (e.g., 'ORD-1005').
    """
    try:
        result = order_service.get_order_status(order_id)
        log_agent_event("TOOL_EXECUTION_SUCCESS", f"get_order_status executed for {order_id}", {"result": result})
        return result
    except AppBaseException as e:
        log_agent_event("TOOL_EXECUTION_ERROR", f"get_order_status failed: {e.message}", {"error_code": e.error_code})
        return {
            "success": False,
            "error_code": e.error_code,
            "error": e.message
        }
    except Exception as e:
        log_agent_event("TOOL_EXECUTION_ERROR", f"get_order_status unhandled error: {str(e)}")
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": "The order service encountered an unexpected error. Please try again or contact human support."
        }


def get_order_details_tool(order_id: str) -> Dict[str, Any]:
    """
    Retrieve full operational details for an order including dishes, pricing, address, and payment status.
    Arguments:
        order_id: The unique identifier of the order (e.g., 'ORD-1001').
    """
    try:
        result = order_service.get_order_details(order_id)
        log_agent_event("TOOL_EXECUTION_SUCCESS", f"get_order_details executed for {order_id}", {"order_id": order_id})
        return result
    except AppBaseException as e:
        log_agent_event("TOOL_EXECUTION_ERROR", f"get_order_details failed: {e.message}", {"error_code": e.error_code})
        return {
            "success": False,
            "error_code": e.error_code,
            "error": e.message
        }
    except Exception as e:
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": "The order service encountered an unexpected error."
        }


def cancel_order_tool(order_id: str, reason: str = "Customer requested cancellation") -> Dict[str, Any]:
    """
    Attempt to cancel an order based on operational rules.
    Orders can only be cancelled if the kitchen has not begun preparation.
    Arguments:
        order_id: The order identifier.
        reason: The customer's stated reason for cancellation.
    """
    try:
        result = order_service.request_cancellation(order_id, reason)
        log_agent_event("TOOL_EXECUTION_SUCCESS", f"cancel_order executed for {order_id}", {"result": result})
        return result
    except AppBaseException as e:
        return {
            "success": False,
            "error_code": e.error_code,
            "error": e.message
        }
    except Exception as e:
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": "Order cancellation service temporarily unavailable."
        }

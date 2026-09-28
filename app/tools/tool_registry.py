"""
Tool Registry & Dispatcher.
Registers tools, exports Gemini function definitions, and routes tool calls.
"""

from typing import Dict, Any, Callable, List
from app.tools.order_tools import (
    get_order_status_tool,
    get_order_details_tool,
    cancel_order_tool
)
from app.tools.support_tools import (
    create_support_ticket_tool,
    search_restaurant_policies_tool
)
from app.core.logging import logger


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: List[Dict[str, Any]] = []
        self._register_default_tools()

    def _register_default_tools(self):
        # 1. get_order_status
        self.register(
            name="get_order_status",
            func=get_order_status_tool,
            description="Retrieve real-time authoritative order status, ETA, and courier information for a given order ID.",
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The unique order ID such as 'ORD-1005' or 'ORD-1001'."
                    }
                },
                "required": ["order_id"]
            }
        )

        # 2. get_order_details
        self.register(
            name="get_order_details",
            func=get_order_details_tool,
            description="Retrieve complete line items, prices, delivery address, and payment status for an order.",
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The unique order ID."
                    }
                },
                "required": ["order_id"]
            }
        )

        # 3. create_support_ticket
        self.register(
            name="create_support_ticket",
            func=create_support_ticket_tool,
            description="Create a formal support ticket for payment issues, complaints, missing items, refunds, or escalations.",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["Payment", "Order", "Delivery", "Refund", "Technical", "Other"],
                        "description": "Category of the customer issue."
                    },
                    "issue_summary": {
                        "type": "string",
                        "description": "A concise summary of the issue."
                    },
                    "details": {
                        "type": "string",
                        "description": "Full details and background of the customer complaint."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High", "Critical"],
                        "description": "Calculated priority level."
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["Positive", "Neutral", "Frustrated", "Angry", "Urgent"],
                        "description": "Customer sentiment."
                    },
                    "order_id": {
                        "type": "string",
                        "description": "Related order ID if applicable."
                    },
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID if known."
                    },
                    "resolution_action": {
                        "type": "string",
                        "description": "Action taken or recommended for resolution."
                    }
                },
                "required": ["category", "issue_summary", "details"]
            }
        )

        # 4. cancel_order
        self.register(
            name="cancel_order",
            func=cancel_order_tool,
            description="Request cancellation and refund for an order. Operates according to kitchen preparation rules.",
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to cancel."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for cancellation."
                    }
                },
                "required": ["order_id"]
            }
        )

        # 5. search_restaurant_policies
        self.register(
            name="search_restaurant_policies",
            func=search_restaurant_policies_tool,
            description="Search official restaurant policies regarding cancellations, refunds, delivery times, allergens, and operating hours.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query about restaurant policies."
                    }
                },
                "required": ["query"]
            }
        )

    def register(self, name: str, func: Callable, description: str, parameters: Dict[str, Any]):
        """Register a tool callable and its JSON schema definition."""
        self._tools[name] = func
        self._definitions.append({
            "name": name,
            "description": description,
            "parameters": parameters
        })

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Return all tool schema definitions."""
        return self._definitions

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered tool by name with arguments."""
        if tool_name not in self._tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not registered in the tool registry."
            }
        try:
            return self._tools[tool_name](**arguments)
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' failed with error: {str(e)}"
            }


tool_registry = ToolRegistry()

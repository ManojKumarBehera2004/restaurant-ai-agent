"""
Agent Guardrails & Request Intent Router.
"""

import re
from typing import Tuple, Optional
from app.core.security import SecurityGuardrails
from app.core.logging import log_agent_event


class AgentGuardrails:
    """Provides high-level safety, prompt injection detection, and data bounds."""

    @staticmethod
    def validate_input(user_message: str) -> Tuple[bool, Optional[str]]:
        """Run security checks against user input."""
        return SecurityGuardrails.inspect_input(user_message)

    @staticmethod
    def validate_output(agent_response: str) -> str:
        """Sanitize agent output against leaked credentials or sensitive internals."""
        return SecurityGuardrails.inspect_output(agent_response)


class IntentRouter:
    """Classifies user message intent to guide optimal agent execution paths."""

    INTENT_ORDER_TRACKING = "ORDER_TRACKING"
    INTENT_ORDER_DETAILS = "ORDER_DETAILS"
    INTENT_POLICY_INQUIRY = "POLICY_INQUIRY"
    INTENT_COMPLAINT = "COMPLAINT"
    INTENT_ORDER_CANCEL = "ORDER_CANCEL"
    INTENT_GENERAL = "GENERAL"

    @classmethod
    def route(cls, user_message: str) -> str:
        lower = user_message.lower()
        has_order_id = bool(re.search(r'\b(ORD-\d+)\b', user_message, re.IGNORECASE))

        # Check for cancel intent
        if "cancel" in lower:
            return cls.INTENT_ORDER_CANCEL

        # Check for complaints or payment issues
        if any(w in lower for w in ["deducted", "failed", "scam", "wrong item", "missing", "terrible", "complaint", "refund"]):
            return cls.INTENT_COMPLAINT

        # Check for order tracking vs details
        if has_order_id:
            if any(w in lower for w in ["detail", "items", "dish", "recipe", "receipt", "breakdown", "address"]):
                return cls.INTENT_ORDER_DETAILS
            return cls.INTENT_ORDER_TRACKING

        # Check for policy questions
        if any(w in lower for w in ["policy", "hour", "open", "close", "allergy", "allergen", "cutlery", "delivery time", "how long", "fee"]):
            return cls.INTENT_POLICY_INQUIRY

        return cls.INTENT_GENERAL

"""
LLM Abstraction & Service Layer.
Decouples agent logic from specific LLM providers.
Supports Google Gemini with fallback/mock capability for offline development & tests.
"""

import os
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger, log_agent_event
from app.core.exceptions import LLMServiceError

try:
    import google.generativeai as gai
    from google.generativeai.types import FunctionDeclaration, Tool
except ImportError:
    gai = None


class LLMToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class LLMMessageResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[LLMToolCall] = []
    finish_reason: str = "stop"
    raw_response: Optional[Any] = None


class BaseLLMService(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate a single text response."""
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured JSON response."""
        pass

    @abstractmethod
    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: str,
        tool_definitions: List[Dict[str, Any]]
    ) -> LLMMessageResponse:
        """Send chat history and tool definitions, returning either text or tool calls."""
        pass


class GeminiLLMService(BaseLLMService):
    """Google Gemini API implementation using official Google Generative AI SDK."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        if not gai:
            raise LLMServiceError("gemini", "google-generativeai package is not installed.")
        if not self.api_key:
            raise LLMServiceError("gemini", "GEMINI_API_KEY is not configured in environment.")
        gai.configure(api_key=self.api_key)

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            model = gai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            return response.text if response.text else ""
        except Exception as e:
            logger.error(f"Gemini generate_text error: {e}")
            raise LLMServiceError("gemini", str(e))

    def generate_structured(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        try:
            model = gai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction,
                generation_config={"response_mime_type": "application/json"}
            )
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Clean possible markdown code fences if returned
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Gemini generate_structured error: {e}")
            raise LLMServiceError("gemini", str(e))

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: str,
        tool_definitions: List[Dict[str, Any]]
    ) -> LLMMessageResponse:
        try:
            # Build tools list for Gemini
            model = gai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction,
            )

            # Build conversational contents
            gemini_contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_contents.append({"role": role, "parts": [msg["content"]]})

            # Check if tools are requested via function calling
            # Gemini Python SDK supports passing python functions or tool dicts
            # For maximum compatibility across SDK versions, we pass standard prompts with JSON tool schema
            # if native function binding is configured
            response = model.generate_content(gemini_contents)

            # Check for function calls in response parts
            tool_calls = []
            content_text = ""

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = {k: v for k, v in fc.args.items()}
                        tool_calls.append(LLMToolCall(tool_name=fc.name, arguments=args))
                    elif hasattr(part, "text") and part.text:
                        content_text += part.text

            return LLMMessageResponse(
                content=content_text if content_text else None,
                tool_calls=tool_calls,
                finish_reason="tool_calls" if tool_calls else "stop"
            )
        except Exception as e:
            logger.error(f"Gemini chat_with_tools error: {e}")
            raise LLMServiceError("gemini", str(e))


class MockLLMService(BaseLLMService):
    """
    High-fidelity Mock LLM Service for offline development, local unit tests,
    and fallback operation when no Gemini API key is configured.
    """

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        return f"Mock response grounded in provided instructions."

    def generate_structured(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        lower = prompt.lower()
        if "payment" in lower or "deducted" in lower:
            return {
                "category": "Payment",
                "sentiment": "Urgent",
                "urgency": "High",
                "confidence_score": 0.96,
                "reasoning": "Payment was captured but order is unconfirmed/failed.",
                "suggested_action": "Raise high priority ticket for payment reconciliation.",
                "extracted_order_id": "ORD-1006" if "ord-1006" in lower else None
            }
        elif "cancel" in lower:
            return {
                "category": "Order",
                "sentiment": "Neutral",
                "urgency": "Medium",
                "confidence_score": 0.90,
                "reasoning": "Customer inquiring about cancellation terms.",
                "suggested_action": "Check order status and verify kitchen preparation state.",
                "extracted_order_id": None
            }
        else:
            return {
                "category": "Order",
                "sentiment": "Neutral",
                "urgency": "Medium",
                "confidence_score": 0.88,
                "reasoning": "General support inquiry.",
                "suggested_action": "Provide helpful guidance to customer.",
                "extracted_order_id": None
            }

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: str,
        tool_definitions: List[Dict[str, Any]]
    ) -> LLMMessageResponse:
        last_msg = messages[-1]["content"] if messages else ""
        lower = last_msg.lower()

        # Tool 1: get_order_status
        order_match = re.search(r'\b(ORD-\d+)\b', last_msg, re.IGNORECASE)
        if order_match and any(w in lower for w in ["where is", "status", "track", "eta", "when will"]):
            order_id = order_match.group(1).upper()
            return LLMMessageResponse(
                content=None,
                tool_calls=[LLMToolCall(tool_name="get_order_status", arguments={"order_id": order_id})],
                finish_reason="tool_calls"
            )

        # Tool 2: get_order_details
        if order_match and any(w in lower for w in ["detail", "items", "receipt", "breakdown", "address"]):
            order_id = order_match.group(1).upper()
            return LLMMessageResponse(
                content=None,
                tool_calls=[LLMToolCall(tool_name="get_order_details", arguments={"order_id": order_id})],
                finish_reason="tool_calls"
            )

        # Tool 3: create_support_ticket for payment deduction or complaints
        if any(w in lower for w in ["deducted", "failed", "scam", "wrong food", "allergy", "terrible", "urgent"]):
            return LLMMessageResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        tool_name="create_support_ticket",
                        arguments={
                            "category": "Payment" if "payment" in lower or "deducted" in lower else "Order",
                            "issue_summary": last_msg[:50],
                            "details": last_msg,
                            "priority": "High" if "payment" in lower or "deducted" in lower else "Medium",
                            "sentiment": "Urgent" if "deducted" in lower else "Frustrated",
                            "order_id": order_match.group(1).upper() if order_match else None
                        }
                    )
                ],
                finish_reason="tool_calls"
            )

        # Tool 4: Policy search
        if any(w in lower for w in ["cancel", "refund", "policy", "hours", "allergen", "cutlery", "time", "late"]):
            return LLMMessageResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        tool_name="search_restaurant_policies",
                        arguments={"query": last_msg}
                    )
                ],
                finish_reason="tool_calls"
            )

        # Direct response fallback
        return LLMMessageResponse(
            content="Hello! I am your AI Restaurant Support Agent. I can help you track orders, answer questions about our cancellation and delivery policies, or assist with complaints and refund requests. How can I help you today?",
            tool_calls=[],
            finish_reason="stop"
        )


def is_valid_api_key(key: Optional[str]) -> bool:
    if not key or not isinstance(key, str):
        return False
    cleaned = key.strip().lower()
    return bool(cleaned and not any(p in cleaned for p in ["your-", "your_", "placeholder", "key_here", "example"]))


def get_llm_service() -> BaseLLMService:
    """Factory providing the configured LLM service with auto-detection."""
    if settings.LLM_PROVIDER.lower() == "gemini" and is_valid_api_key(settings.GEMINI_API_KEY) and gai:
        try:
            return GeminiLLMService()
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini LLM ({e}). Falling back to Mock LLM.")
            return MockLLMService()
    return MockLLMService()


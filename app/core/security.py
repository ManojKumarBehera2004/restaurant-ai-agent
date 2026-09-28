"""
Security & Guardrails Module.
Implements prompt injection defense, unauthorized data access blocking,
and output redaction.
"""

import re
from typing import Tuple, Optional
from app.core.logging import logger, log_agent_event


class SecurityGuardrails:
    """Security engine for agent input & output validation."""

    # Known prompt-injection and jailbreak signatures
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r'(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)', re.IGNORECASE),
        re.compile(r'(?i)disregard\s+(all\s+)?(system|initial)\s+(instructions|directives)', re.IGNORECASE),
        re.compile(r'(?i)show\s+me\s+(every|all)\s+(customer|user|order|client)\s+(order|data|record|account|detail)', re.IGNORECASE),
        re.compile(r'(?i)dump\s+(the\s+)?(database|all\s+tables|schema|orders)', re.IGNORECASE),
        re.compile(r'(?i)(what\s+is|show\s+me|reveal|print|expose)\s+(your\s+)?(system\s+prompt|hidden\s+instruction|developer\s+mode|api[_-]?key|secret)', re.IGNORECASE),
        re.compile(r'(?i)you\s+are\s+now\s+(in\s+developer\s+mode|DAN|an\s+unrestricted\s+ai|jailbroken)', re.IGNORECASE),
        re.compile(r'(?i)(drop\s+table|delete\s+from|insert\s+into|union\s+select|\'(\s*)or(\s*)\'1\'=\'1)', re.IGNORECASE),
        re.compile(r'(?i)(exec|execute|eval|os\.system|subprocess)\s*\(', re.IGNORECASE),
    ]

    # Sensitive strings that must never appear in agent responses
    SENSITIVE_OUTPUT_PATTERNS = [
        re.compile(r'(?i)AIza[0-9A-Za-z-_]{35}'),  # Google API key pattern
        re.compile(r'(?i)sk-[a-zA-Z0-9]{32,}'),    # OpenAI-like key pattern
        re.compile(r'(?i)password\s*=\s*["\'][^"\']+["\']'),
        re.compile(r'(?i)db_password|api_secret|gemini_api_key', re.IGNORECASE),
    ]

    @classmethod
    def inspect_input(cls, user_input: str) -> Tuple[bool, Optional[str]]:
        """
        Inspect user message for security violations or prompt injection attempts.
        Returns:
            (is_safe, refusal_reason)
        """
        if not user_input or not isinstance(user_input, str):
            return True, None

        cleaned_input = user_input.strip()

        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            match = pattern.search(cleaned_input)
            if match:
                matched_text = match.group(0)
                log_agent_event(
                    "SECURITY_GUARDRAIL_TRIGGERED",
                    f"Prompt injection attempt blocked: {matched_text}",
                    {"input_snippet": cleaned_input[:100], "matched_rule": pattern.pattern}
                )
                return False, (
                    "I cannot comply with requests that ask to ignore security guidelines, "
                    "reveal system prompts, or access unauthorized operational data. "
                    "How can I assist you with your specific restaurant order or support inquiry?"
                )

        return True, None

    @classmethod
    def sanitize_order_id(cls, order_id: str) -> str:
        """Validate and sanitize an order ID string to prevent injection."""
        if not order_id:
            return ""
        # Remove any leading/trailing spaces and dangerous characters
        cleaned = re.sub(r'[^A-Za-z0-9\-_]', '', order_id.strip())
        return cleaned.upper()

    @classmethod
    def inspect_output(cls, agent_output: str) -> str:
        """
        Inspect the LLM's final response for accidental secrets or system leaks.
        Redacts any sensitive matching patterns.
        """
        if not agent_output:
            return agent_output

        sanitized = agent_output
        for pattern in cls.SENSITIVE_OUTPUT_PATTERNS:
            if pattern.search(sanitized):
                log_agent_event(
                    "SECURITY_OUTPUT_SCRUBBED",
                    "Redacted potential secret pattern from agent output.",
                    {"pattern": pattern.pattern}
                )
                sanitized = pattern.sub("[REDACTED_CREDENTIAL]", sanitized)

        return sanitized

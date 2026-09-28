"""
Complaint Classifier & Sentiment/Urgency Assessor.
Analyzes customer complaints into structured categories, sentiments, and validated priorities.
"""

import re
import json
from typing import Optional, Dict, Any
from app.models.schemas import ComplaintClassificationResult
from app.core.logging import logger, log_agent_event


class ComplaintClassifier:
    """Classifies complaints and assigns priority based on severity rules."""

    @staticmethod
    def _rule_based_classify(text: str) -> ComplaintClassificationResult:
        """Deterministic rule-based classification fallback."""
        lower = text.lower()

        # Extract order ID if present (e.g. ORD-1005)
        order_match = re.search(r'\b(ORD-\d+)\b', text, re.IGNORECASE)
        extracted_order = order_match.group(1).upper() if order_match else None

        # Determine Category
        if any(w in lower for w in ["payment", "charged", "deducted", "bank", "credit card", "debited", "billing"]):
            category = "Payment"
        elif any(w in lower for w in ["refund", "money back", "reimburse", "return money"]):
            category = "Refund"
        elif any(w in lower for w in ["delivery", "driver", "courier", "late", "eta", "never arrived", "cold food", "wrong address"]):
            category = "Delivery"
        elif any(w in lower for w in ["app", "crash", "website", "bug", "error code", "technical", "login"]):
            category = "Technical"
        elif any(w in lower for w in ["order", "missing", "wrong item", "spilled", "burnt", "undercooked", "allergy"]):
            category = "Order"
        else:
            category = "Other"

        # Determine Sentiment
        if any(w in lower for w in ["furious", "terrible", "unacceptable", "scam", "disaster", "angry", "ridiculous"]):
            sentiment = "Angry"
        elif any(w in lower for w in ["urgent", "immediately", "asap", "emergency", "hurry", "right now"]):
            sentiment = "Urgent"
        elif any(w in lower for w in ["frustrated", "disappointed", "waiting too long", "annoyed", "failed"]):
            sentiment = "Frustrated"
        elif any(w in lower for w in ["thanks", "great", "good", "please help"]):
            sentiment = "Neutral"
        else:
            sentiment = "Neutral"

        # Determine Urgency / Priority (Deterministic rules)
        # 1. Critical: Allergy emergency, severe contamination, safety hazard
        if any(w in lower for w in ["allergy", "allergic", "hospital", "poison", "glass", "insect", "hazard"]):
            urgency = "Critical"
            reasoning = "Health or safety risk detected in complaint."
            suggested_action = "Immediate manager escalation and customer contact."
        # 2. High: Payment deducted + order failed, completely missing delivery, extreme anger
        elif (category == "Payment" and any(w in lower for w in ["deducted", "failed", "charged"])) or sentiment in ["Angry", "Urgent"]:
            urgency = "High"
            reasoning = "Financial discrepancy or high customer distress requires expedited triage."
            suggested_action = "Escalate to payment support desk / verify transaction logs."
        # 3. Medium: Delivery delays, missing side item, cancellation query
        elif category in ["Delivery", "Order", "Refund"] or sentiment == "Frustrated":
            urgency = "Medium"
            reasoning = "Standard order disruption requiring investigation."
            suggested_action = "Check order status and arrange compensation or replacement."
        else:
            urgency = "Low"
            reasoning = "General inquiry or minor feedback."
            suggested_action = "Standard response and customer assistance."

        return ComplaintClassificationResult(
            category=category,
            sentiment=sentiment,
            urgency=urgency,
            confidence_score=0.92,
            reasoning=reasoning,
            suggested_action=suggested_action,
            extracted_order_id=extracted_order
        )

    @classmethod
    def classify(cls, complaint_text: str, llm_service=None) -> ComplaintClassificationResult:
        """
        Classify complaint using LLM if available, validating against Pydantic schema.
        Falls back to rule-based engine if LLM is unavailable or fails schema validation.
        """
        if not complaint_text:
            return cls._rule_based_classify("General inquiry")

        if llm_service and hasattr(llm_service, "generate_structured"):
            prompt = f"""
Analyze the following customer complaint and classify it into structured operational triage data.
Customer Message: "{complaint_text}"

Return JSON matching this schema:
{{
  "category": "Payment" | "Order" | "Delivery" | "Refund" | "Technical" | "Other",
  "sentiment": "Positive" | "Neutral" | "Frustrated" | "Angry" | "Urgent",
  "urgency": "Low" | "Medium" | "High" | "Critical",
  "confidence_score": 0.0 to 1.0,
  "reasoning": "brief explanation",
  "suggested_action": "recommended operational triage action",
  "extracted_order_id": "e.g. ORD-1005 or null"
}}
"""
            try:
                result_dict = llm_service.generate_structured(prompt)
                if result_dict:
                    validated = ComplaintClassificationResult(**result_dict)
                    log_agent_event("CLASSIFICATION_LLM_SUCCESS", "LLM structured classification succeeded", validated.model_dump())
                    return validated
            except Exception as e:
                logger.warning(f"LLM structured classification failed ({e}). Falling back to rule-based classifier.")

        # Fallback to deterministic rule engine
        result = cls._rule_based_classify(complaint_text)
        log_agent_event("CLASSIFICATION_RULE_BASED", "Rule-based classification applied", result.model_dump())
        return result

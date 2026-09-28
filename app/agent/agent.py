"""
AI Restaurant Support & Operations Agent Orchestrator.
Coordinates reasoning, tool calling, RAG retrieval, guardrails, and multi-turn context.
"""

import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.core.logging import logger, log_agent_event
from app.core.security import SecurityGuardrails
from app.models.schemas import ChatResponse, ToolCallRecord, RAGSourceDoc, TicketResponse
from app.agent.prompts import SYSTEM_PROMPT, GROUNDED_RESPONSE_PROMPT_TEMPLATE
from app.agent.context import context_manager
from app.agent.router import IntentRouter, AgentGuardrails
from app.tools.tool_registry import tool_registry
from app.rag.retriever import retriever
from app.workflows.complaint_workflow import ComplaintWorkflow
from app.services.llm_service import get_llm_service, BaseLLMService


class RestaurantAgent:
    def __init__(self, llm_service: Optional[BaseLLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def process_message(
        self,
        message: str,
        session_id: str = "default_session",
        customer_id: str = "CUST-001"
    ) -> ChatResponse:
        """
        Main execution entry point for processing a customer message.
        """
        start_time = time.time()
        tool_records: List[ToolCallRecord] = []
        rag_sources: List[RAGSourceDoc] = []
        created_ticket: Optional[TicketResponse] = None

        # ---------------------------------------------------------
        # Step 1: Input Guardrails & Security Check
        # ---------------------------------------------------------
        is_safe, refusal_reason = AgentGuardrails.validate_input(message)
        if not is_safe:
            execution_time = (time.time() - start_time) * 1000
            context_manager.record_message(session_id, "user", message)
            context_manager.record_message(session_id, "assistant", refusal_reason)
            return ChatResponse(
                session_id=session_id,
                reply=refusal_reason,
                tool_calls=[],
                rag_sources=[],
                security_flag=True,
                intent="SECURITY_BLOCKED",
                execution_time_ms=round(execution_time, 2),
                token_usage_estimate=len(message.split()) + len(refusal_reason.split())
            )

        # ---------------------------------------------------------
        # Step 2: Intent Routing & Context Retrieval
        # ---------------------------------------------------------
        intent = IntentRouter.route(message)
        history = context_manager.get_session_history(session_id, limit=6)
        log_agent_event("AGENT_INVOCATION", f"Processing user message with intent: {intent}", {
            "session_id": session_id,
            "intent": intent,
            "message_snippet": message[:100]
        })

        reply_text = ""
        operational_context = []

        # ---------------------------------------------------------
        # Step 3: Tool Execution & RAG Grounding based on Intent
        # ---------------------------------------------------------
        order_match = re.search(r'\b(ORD-\d+)\b', message, re.IGNORECASE)
        extracted_order_id = order_match.group(1).upper() if order_match else None

        # Case A: Order Status Inquiry
        if intent == IntentRouter.INTENT_ORDER_TRACKING:
            if extracted_order_id:
                t0 = time.time()
                tool_res = tool_registry.execute("get_order_status", {"order_id": extracted_order_id})
                t_exec = (time.time() - t0) * 1000
                is_ok = tool_res.get("success", False)
                err_msg = tool_res.get("error") if not is_ok else None

                tool_records.append(ToolCallRecord(
                    tool_name="get_order_status",
                    arguments={"order_id": extracted_order_id},
                    result=tool_res,
                    success=is_ok,
                    error_message=err_msg,
                    execution_time_ms=round(t_exec, 2)
                ))

                if is_ok:
                    status = tool_res["status"]
                    msg = tool_res["message"]
                    eta = tool_res.get("estimated_delivery_minutes")
                    partner = tool_res.get("delivery_partner")

                    reply_text = f"Here is the status for your order **{extracted_order_id}**:\n\n"
                    reply_text += f"- **Current Status:** {status}\n"
                    reply_text += f"- **Details:** {msg}\n"
                    if eta is not None and eta > 0:
                        reply_text += f"- **Estimated Time of Arrival:** {eta} minutes\n"
                    if partner:
                        reply_text += f"- **Delivery Partner:** {partner}\n"
                else:
                    reply_text = f"I checked our operational system for order **{extracted_order_id}**, but encountered an issue:\n\n"
                    reply_text += f"*{err_msg or 'Order information is currently unavailable.'}*\n\n"
                    reply_text += "Please double check your order number or let me know if you would like me to connect you with a representative."
            else:
                reply_text = "Could you please provide your Order ID (for example, ORD-1005) so I can check its real-time status for you?"

        # Case B: Order Full Details Inquiry
        elif intent == IntentRouter.INTENT_ORDER_DETAILS:
            if extracted_order_id:
                t0 = time.time()
                tool_res = tool_registry.execute("get_order_details", {"order_id": extracted_order_id})
                t_exec = (time.time() - t0) * 1000
                is_ok = tool_res.get("success", False)

                tool_records.append(ToolCallRecord(
                    tool_name="get_order_details",
                    arguments={"order_id": extracted_order_id},
                    result=tool_res,
                    success=is_ok,
                    error_message=tool_res.get("error") if not is_ok else None,
                    execution_time_ms=round(t_exec, 2)
                ))

                if is_ok:
                    items_list = tool_res.get("items", [])
                    items_formatted = "\n".join([f"  • {it.get('quantity')}x {it.get('name')} (${it.get('unit_price'):.2f})" for it in items_list])
                    reply_text = f"Here are the details for order **{extracted_order_id}**:\n\n"
                    reply_text += f"- **Status:** {tool_res.get('status')}\n"
                    reply_text += f"- **Items Ordered:**\n{items_formatted}\n"
                    reply_text += f"- **Total Amount:** ${tool_res.get('total'):.2f} ({tool_res.get('payment_status')})\n"
                    reply_text += f"- **Delivery Address:** {tool_res.get('delivery_address')}\n"
                else:
                    reply_text = f"I could not retrieve details for order **{extracted_order_id}**: {tool_res.get('error')}"
            else:
                reply_text = "Please share your order number (e.g. ORD-1001) so I can pull up the itemized breakdown."

        # Case C: Order Cancellation Request
        elif intent == IntentRouter.INTENT_ORDER_CANCEL:
            # First retrieve relevant cancellation policy from RAG
            rag_docs = retriever.search(message, top_k=2)
            rag_sources.extend(rag_docs)

            if extracted_order_id:
                t0 = time.time()
                tool_res = tool_registry.execute("cancel_order", {"order_id": extracted_order_id, "reason": message})
                t_exec = (time.time() - t0) * 1000
                is_ok = tool_res.get("success", False)

                tool_records.append(ToolCallRecord(
                    tool_name="cancel_order",
                    arguments={"order_id": extracted_order_id, "reason": message},
                    result=tool_res,
                    success=is_ok,
                    error_message=tool_res.get("error") if not is_ok else None,
                    execution_time_ms=round(t_exec, 2)
                ))

                if tool_res.get("cancelled"):
                    reply_text = f"Your order **{extracted_order_id}** has been cancelled successfully.\n\n"
                    reply_text += f"{tool_res.get('message')}\n"
                    reply_text += "\n*According to our refund policy, store credit is instant, while card refunds take 3-5 business days.*"
                else:
                    reply_text = f"Unable to cancel order **{extracted_order_id}** automatically.\n\n"
                    reply_text += f"**Reason:** {tool_res.get('message')}\n\n"
                    if rag_docs:
                        reply_text += f"**Policy Rule:** {rag_docs[0].content[:200]}...\n\n"
                    reply_text += "Would you like me to open a support ticket for managerial review?"
            else:
                # General policy explanation about cancellations
                if rag_docs:
                    reply_text = "Here is our official **Order Cancellation Policy**:\n\n"
                    reply_text += f"{rag_docs[0].content}\n\n"
                    reply_text += "If you have an active order you wish to cancel, please provide the **Order ID**."
                else:
                    reply_text = "Orders can only be cancelled free of charge before the kitchen begins food preparation. Once cooking starts, orders cannot be self-cancelled."

        # Case D: Policy Inquiry (RAG)
        elif intent == IntentRouter.INTENT_POLICY_INQUIRY:
            rag_docs = retriever.search(message, top_k=3)
            rag_sources.extend(rag_docs)

            if rag_docs:
                top_doc = rag_docs[0]
                reply_text = f"{top_doc.content}\n\n"
                reply_text += f"*(Source: {top_doc.title})*"
            else:
                reply_text = (
                    "I searched our official restaurant knowledge base, but could not find a documented policy "
                    "answering your specific question. Would you like me to open a support ticket so our team can assist you directly?"
                )

        # Case E: Complaint / Automated Support Ticket Creation Workflow
        elif intent == IntentRouter.INTENT_COMPLAINT:
            wf_result = ComplaintWorkflow.process_complaint(
                complaint_text=message,
                customer_id=customer_id,
                order_id=extracted_order_id,
                llm_service=self.llm_service
            )

            ticket_dict = wf_result.get("ticket")
            classification = wf_result.get("classification", {})

            if ticket_dict:
                created_ticket = TicketResponse(
                    id=ticket_dict["id"],
                    category=ticket_dict["category"],
                    priority=ticket_dict["priority"],
                    sentiment=ticket_dict["sentiment"],
                    issue_summary=ticket_dict["issue_summary"],
                    details=ticket_dict["details"],
                    customer_id=ticket_dict.get("customer_id"),
                    order_id=ticket_dict.get("order_id"),
                    resolution_action=ticket_dict.get("resolution_action"),
                    status=ticket_dict["status"],
                    created_at=datetime.fromisoformat(ticket_dict["created_at"]) if ticket_dict.get("created_at") else datetime.utcnow()
                )

                tool_records.append(ToolCallRecord(
                    tool_name="create_support_ticket",
                    arguments={
                        "category": classification.get("category", "Payment"),
                        "issue_summary": ticket_dict["issue_summary"],
                        "details": message,
                        "priority": classification.get("urgency", "High"),
                        "order_id": extracted_order_id
                    },
                    result=ticket_dict,
                    success=True,
                    execution_time_ms=12.0
                ))

                reply_text = (
                    f"I understand your concern and I apologize for the inconvenience. "
                    f"I have automatically created a support ticket for our operations and billing team:\n\n"
                    f"- **Ticket ID:** `{created_ticket.id}`\n"
                    f"- **Category:** {created_ticket.category}\n"
                    f"- **Priority:** {created_ticket.priority} (Assessed Sentiment: {created_ticket.sentiment})\n"
                    f"- **Next Action:** {classification.get('suggested_action', 'Our support specialist is reviewing your case.')}\n\n"
                    f"Our support desk has been alerted and will resolve this promptly. Is there anything else I can help you with?"
                )
            else:
                reply_text = "I apologize for the issue. I was unable to automatically generate a ticket, but our support line is available at 1-800-555-FOOD."

        # Case F: General / Fallback Conversation
        else:
            # Check if user asked something that matches policy RAG
            rag_docs = retriever.search(message, top_k=2)
            if rag_docs:
                rag_sources.extend(rag_docs)
                reply_text = f"{rag_docs[0].content}\n\n*(Source: {rag_docs[0].title})*"
            else:
                reply_text = (
                    "Hello! I am the Gourmet Bistro Support Agent. I can assist you with:\n"
                    "• **Order Tracking & Details** (e.g. *'Where is my order ORD-1005?'*)\n"
                    "• **Restaurant Policies & FAQs** (e.g. *'Can I cancel after the restaurant accepts?'*)\n"
                    "• **Billing & Complaints** (e.g. *'Payment was deducted but order failed'*)\n"
                    "• **Operating Hours, Allergen Info & Delivery Times**\n\n"
                    "How can I help you today?"
                )

        # ---------------------------------------------------------
        # Step 4: Output Guardrails & Sanitization
        # ---------------------------------------------------------
        sanitized_reply = AgentGuardrails.validate_output(reply_text)

        # ---------------------------------------------------------
        # Step 5: Persistence & Observability Metrics
        # ---------------------------------------------------------
        execution_time = (time.time() - start_time) * 1000
        token_estimate = len(message.split()) + len(sanitized_reply.split()) + sum(len(str(t.result).split()) for t in tool_records)

        # Persist conversation turn
        context_manager.record_message(
            session_id=session_id,
            role="user",
            content=message
        )
        context_manager.record_message(
            session_id=session_id,
            role="assistant",
            content=sanitized_reply,
            tool_calls=[t.model_dump() for t in tool_records],
            rag_sources=[r.model_dump() for r in rag_sources]
        )

        return ChatResponse(
            session_id=session_id,
            reply=sanitized_reply,
            tool_calls=tool_records,
            rag_sources=rag_sources,
            security_flag=False,
            intent=intent,
            execution_time_ms=round(execution_time, 2),
            token_usage_estimate=token_estimate,
            created_ticket=created_ticket
        )


agent_instance = RestaurantAgent()

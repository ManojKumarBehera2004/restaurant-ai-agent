"""
Health, Observability, RAG Search, and Diagnostic Endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import RECENT_LOGS
from app.models.database import get_db
from app.models.schemas import HealthResponse, DiagnosticToggleRequest, RAGSourceDoc
from app.rag.retriever import retriever
from app.repositories.conversation_repository import ConversationRepository

router = APIRouter(tags=["Health & Observability"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """System health check and diagnostic state."""
    vector_count = retriever.collection.count() if retriever.collection else len(retriever._in_memory_docs)
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.GEMINI_MODEL,
        vector_store_status=f"Active ({vector_count} policy chunks indexed)",
        database_status="Connected (SQLite)",
        order_outage_simulation_active=settings.SIMULATE_ORDER_SERVICE_OUTAGE
    )


@router.post("/api/debug/simulate-outage")
async def toggle_simulate_outage(req: DiagnosticToggleRequest):
    """
    Toggle simulated tool/API outages for live evaluation testing.
    Specifically tests Scenario: 'The order API is unavailable'.
    """
    if req.simulate_order_service_outage is not None:
        settings.SIMULATE_ORDER_SERVICE_OUTAGE = req.simulate_order_service_outage
    if req.simulate_llm_timeout is not None:
        settings.SIMULATE_LLM_TIMEOUT = req.simulate_llm_timeout

    return {
        "success": True,
        "simulate_order_service_outage": settings.SIMULATE_ORDER_SERVICE_OUTAGE,
        "simulate_llm_timeout": settings.SIMULATE_LLM_TIMEOUT,
        "message": "Operational failure simulation flags updated."
    }


@router.get("/api/observability/logs")
async def get_observability_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve recent structured execution and security audit logs."""
    repo = ConversationRepository(db)
    db_audits = repo.list_recent_audits(limit=limit)

    return {
        "recent_in_memory_traces": RECENT_LOGS[-limit:],
        "database_audit_records": [
            {
                "id": a.id,
                "event_type": a.event_type,
                "session_id": a.session_id,
                "message": a.message,
                "payload": a.payload_json,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None
            }
            for a in db_audits
        ]
    }


@router.get("/api/rag/search", response_model=List[RAGSourceDoc])
async def search_policies_rag(q: str, top_k: int = 3, min_score: float = 0.5):
    """Directly query the RAG vector store to test policy retrieval and score thresholds."""
    return retriever.search(q, top_k=top_k, min_score=min_score)

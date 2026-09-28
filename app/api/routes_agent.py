"""
Agent API Endpoints.
Handles chat conversations, session history, and session reset.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.schemas import ChatRequest, ChatResponse
from app.models.database import get_db
from app.agent.agent import agent_instance
from app.agent.context import ContextManager
from app.repositories.conversation_repository import ConversationRepository

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(req: ChatRequest):
    """
    Main conversational agent endpoint.
    Processes natural language queries, coordinates tools, RAG policies, and workflows.
    """
    try:
        response = agent_instance.process_message(
            message=req.message,
            session_id=req.session_id,
            customer_id=req.customer_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent processing error: {str(e)}")


@router.get("/history/{session_id}")
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """Retrieve full conversation history for a given session ID."""
    repo = ConversationRepository(db)
    messages = repo.get_history(session_id)
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls_json,
                "rag_sources": m.rag_sources_json,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in messages
        ]
    }


@router.post("/reset/{session_id}")
async def reset_session(session_id: str, db: Session = Depends(get_db)):
    """Clear conversation history for a session."""
    repo = ConversationRepository(db)
    deleted_count = repo.clear_history(session_id)
    return {
        "success": True,
        "session_id": session_id,
        "deleted_messages_count": deleted_count,
        "message": f"Session {session_id} memory cleared successfully."
    }

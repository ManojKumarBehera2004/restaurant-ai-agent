"""
Conversation Context & Session Memory Manager.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.repositories.conversation_repository import ConversationRepository
from app.models.database import SessionLocal


class ContextManager:
    """Manages short-term conversation memory and persistence across turns."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_session(self) -> Session:
        return self.db if self.db else SessionLocal()

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Retrieve recent conversation history formatted for LLM."""
        session = self._get_session()
        try:
            repo = ConversationRepository(session)
            messages = repo.get_history(session_id, limit=limit)
            return [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role in ["user", "assistant"]
            ]
        finally:
            if not self.db:
                session.close()

    def record_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        rag_sources: Optional[List[Dict[str, Any]]] = None
    ):
        """Persist a message into the conversation history."""
        session = self._get_session()
        try:
            repo = ConversationRepository(session)
            repo.add_message(session_id, role, content, tool_calls, rag_sources)
        finally:
            if not self.db:
                session.close()

    def clear_session(self, session_id: str):
        """Clear conversation history for a session."""
        session = self._get_session()
        try:
            repo = ConversationRepository(session)
            repo.clear_history(session_id)
        finally:
            if not self.db:
                session.close()


context_manager = ContextManager()

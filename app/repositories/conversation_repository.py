"""
Conversation and Audit Logging Repository.
Maintains persistent chat session history and security/audit trails.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import ConversationMessageEntity, AuditLogEntity


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        rag_sources: Optional[List[Dict[str, Any]]] = None
    ) -> ConversationMessageEntity:
        """Store a new chat message in the session history."""
        msg = ConversationMessageEntity(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls_json=json.dumps(tool_calls) if tool_calls else None,
            rag_sources_json=json.dumps(rag_sources) if rag_sources else None,
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_history(self, session_id: str, limit: int = 20) -> List[ConversationMessageEntity]:
        """Fetch recent conversation messages for a session."""
        return self.db.query(ConversationMessageEntity).filter(
            ConversationMessageEntity.session_id == session_id
        ).order_by(ConversationMessageEntity.id.asc()).limit(limit).all()

    def clear_history(self, session_id: str) -> int:
        """Clear all messages for a session."""
        deleted = self.db.query(ConversationMessageEntity).filter(
            ConversationMessageEntity.session_id == session_id
        ).delete()
        self.db.commit()
        return deleted

    def log_audit(
        self,
        event_type: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AuditLogEntity:
        """Record an audit log entry in the database."""
        entry = AuditLogEntity(
            event_type=event_type,
            session_id=session_id,
            message=message,
            payload_json=json.dumps(payload) if payload else None,
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_recent_audits(self, limit: int = 50) -> List[AuditLogEntity]:
        """List recent audit log records."""
        return self.db.query(AuditLogEntity).order_by(
            AuditLogEntity.id.desc()
        ).limit(limit).all()

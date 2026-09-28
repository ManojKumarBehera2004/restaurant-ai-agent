"""
RAG Retriever and Vector Store Manager.
Manages ChromaDB persistent collection and semantic search over restaurant policies.
"""

import os
import math
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging import logger
from app.models.schemas import RAGSourceDoc
from app.rag.embeddings import get_embedding_service, BaseEmbeddingService
from app.rag.ingestion import load_and_chunk_policies


class PolicyRetriever:
    """Manages policy indexing and vector similarity search."""

    def __init__(self, embedding_service: Optional[BaseEmbeddingService] = None):
        self.embedding_service = embedding_service or get_embedding_service()
        self.persist_dir = settings.CHROMA_PERSIST_DIR
        self.collection_name = settings.RAG_COLLECTION_NAME
        self.client = None
        self.collection = None
        self._in_memory_docs: List[Dict[str, Any]] = []
        self._initialize_store()

    def _initialize_store(self):
        """Initialize ChromaDB collection and index documents if empty."""
        os.makedirs(self.persist_dir, exist_ok=True)
        try:
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            if self.collection.count() == 0:
                self.index_documents()
            else:
                logger.info(f"Connected to existing ChromaDB collection with {self.collection.count()} chunks.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization encountered issue ({e}). Using in-memory vector store.")
            self._initialize_in_memory()

    def _initialize_in_memory(self):
        """Fallback in-memory vector store."""
        chunks = load_and_chunk_policies()
        self._in_memory_docs = []
        for chunk in chunks:
            embedding = self.embedding_service.embed_text(chunk["content"])
            self._in_memory_docs.append({
                "chunk": chunk,
                "embedding": embedding
            })

    def index_documents(self, force_reload: bool = False):
        """Ingest policies and index their embeddings."""
        chunks = load_and_chunk_policies()
        if not chunks:
            logger.warning("No knowledge chunks found to index.")
            return

        if self.collection:
            if force_reload:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )

            ids = [c["id"] for c in chunks]
            documents = [c["content"] for c in chunks]
            metadatas = [{"title": c["title"], "source_file": c["source_file"], "section": c["section"]} for c in chunks]
            embeddings = [self.embedding_service.embed_text(c["content"]) for c in chunks]

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            logger.info(f"Successfully indexed {len(chunks)} chunks in ChromaDB collection '{self.collection_name}'.")

        self._initialize_in_memory()

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two unit-normalized vectors."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return max(0.0, min(1.0, (dot + 1.0) / 2.0))  # Map [-1, 1] to [0, 1]

    def search(self, query: str, top_k: int = None, min_score: float = None) -> List[RAGSourceDoc]:
        """
        Query the knowledge base for relevant policy chunks.
        Returns empty list if no document exceeds min_score.
        """
        top_k = top_k or settings.RAG_TOP_K
        min_score = min_score if min_score is not None else settings.RAG_SCORE_THRESHOLD
        query_embedding = self.embedding_service.embed_text(query)

        results = []

        if self.collection and self.collection.count() > 0:
            try:
                res = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )

                if res and res["documents"] and len(res["documents"][0]) > 0:
                    for doc_text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                        # Chroma cosine distance: score = 1 - distance (or mapped)
                        score = max(0.0, min(1.0, 1.0 - (dist / 2.0) if dist is not None else 0.8))
                        if score >= min_score:
                            results.append(RAGSourceDoc(
                                title=meta.get("title", "Policy Document"),
                                content=doc_text,
                                similarity_score=round(score, 4),
                                source_file=meta.get("source_file", "unknown.md")
                            ))
                    return results
            except Exception as e:
                logger.warning(f"ChromaDB search failed ({e}). Falling back to in-memory cosine search.")

        # In-memory search fallback
        scored_docs = []
        for item in self._in_memory_docs:
            sim = self._cosine_similarity(query_embedding, item["embedding"])
            if sim >= min_score:
                scored_docs.append((sim, item["chunk"]))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        for score, chunk in scored_docs[:top_k]:
            results.append(RAGSourceDoc(
                title=chunk["title"],
                content=chunk["content"],
                similarity_score=round(score, 4),
                source_file=chunk["source_file"]
            ))

        return results

    def format_context_for_prompt(self, docs: List[RAGSourceDoc]) -> str:
        """Format retrieved documents into clear context for LLM prompt."""
        if not docs:
            return "No specific policy document found matching the query. Do NOT invent policies."

        formatted = ["### RETRIEVED RESTAURANT POLICIES (AUTHORITATIVE KNOWLEDGE):"]
        for idx, doc in enumerate(docs, 1):
            formatted.append(f"[{idx}] {doc.title} (Source: {doc.source_file}, Relevance: {doc.similarity_score}):")
            formatted.append(f"{doc.content.strip()}\n")
        return "\n".join(formatted)


# Global singleton retriever instance
retriever = PolicyRetriever()

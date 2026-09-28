"""
Unit Tests for RAG & Policy Retrieval.
"""

import pytest
from app.rag.retriever import PolicyRetriever
from app.rag.ingestion import load_and_chunk_policies


@pytest.fixture
def rag_retriever():
    retriever = PolicyRetriever()
    retriever.index_documents(force_reload=True)
    return retriever


def test_chunking_policies():
    """Verify markdown policies are parsed into coherent chunks."""
    chunks = load_and_chunk_policies()
    assert len(chunks) >= 10
    for chunk in chunks:
        assert "id" in chunk
        assert "title" in chunk
        assert "content" in chunk
        assert len(chunk["content"]) > 10


def test_retrieval_cancellation_policy(rag_retriever):
    """Test policy search for cancellation rules."""
    query = "Can I cancel my order after the restaurant accepts it?"
    docs = rag_retriever.search(query, top_k=3, min_score=0.3)
    assert len(docs) > 0
    combined_content = " ".join([d.content.lower() for d in docs])
    assert "cancel" in combined_content


def test_retrieval_operating_hours(rag_retriever):
    """Test policy search for kitchen hours."""
    query = "What are your operating hours and allergen policies?"
    docs = rag_retriever.search(query, top_k=3, min_score=0.3)
    assert len(docs) > 0
    combined_text = " ".join([d.content.lower() for d in docs])
    assert "operating hours" in combined_text or "10:00" in combined_text or "allergen" in combined_text or "kitchen" in combined_text


def test_out_of_scope_query_handling(rag_retriever):
    """Test behavior when knowledge base does not contain the answer."""
    query = "How do I replace the spark plugs on a 2012 Honda Civic?"
    docs = rag_retriever.search(query, top_k=2, min_score=0.8)
    # Should safely return empty list due to score threshold
    assert len(docs) == 0

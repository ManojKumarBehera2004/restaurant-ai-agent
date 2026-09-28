"""
Standalone CLI script to re-index the Restaurant Knowledge Base into ChromaDB.
Usage:
    python scripts/ingest_knowledge.py
"""

import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag.retriever import PolicyRetriever
from app.core.logging import logger


def main():
    print("==================================================")
    print("Starting Restaurant Policy Ingestion & Indexing...")
    print("==================================================")
    retriever = PolicyRetriever()
    retriever.index_documents(force_reload=True)
    print("Knowledge Base Ingestion Completed Successfully!")


if __name__ == "__main__":
    main()

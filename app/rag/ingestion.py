"""
Knowledge Base Document Ingestion and Chunking.
Parses policy markdown files into structured, semantically coherent chunks.
"""

import os
import re
from typing import List, Dict, Any
from app.core.logging import logger


def load_and_chunk_policies(directory_path: str = "./data/restaurant_policies") -> List[Dict[str, Any]]:
    """
    Read all markdown files in directory and split into section chunks.
    Filters out empty preamble headings so chunks are rich and self-contained.
    """
    chunks = []

    if not os.path.exists(directory_path):
        logger.warning(f"Policies directory not found at: {directory_path}")
        return chunks

    for filename in os.listdir(directory_path):
        if not filename.endswith(".md"):
            continue

        file_path = os.path.join(directory_path, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract main document title
        main_title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        main_title = main_title_match.group(1).strip() if main_title_match else filename

        # Split on section headings (## )
        sections = re.split(r'\n(?=##\s+)', content)

        for i, section in enumerate(sections):
            cleaned_section = section.strip()
            # If this is just the top-level "# Title" with no text under it, skip standalone stub
            if cleaned_section.startswith("# ") and not "\n" in cleaned_section and len(sections) > 1:
                continue

            if not cleaned_section or len(cleaned_section) < 15:
                continue

            # Extract section heading
            heading_match = re.search(r'^(?:#|##)\s+(.+)$', cleaned_section, re.MULTILINE)
            section_title = heading_match.group(1).strip() if heading_match else f"Section {i+1}"

            # Prepend document title to content for rich context
            enriched_content = f"# {main_title} > {section_title}\n\n{cleaned_section}"

            chunk_id = f"{filename}_{i}"
            chunks.append({
                "id": chunk_id,
                "title": f"{main_title} - {section_title}",
                "content": enriched_content,
                "source_file": filename,
                "section": section_title
            })

    logger.info(f"Ingested {len(chunks)} knowledge chunks from {directory_path}")
    return chunks

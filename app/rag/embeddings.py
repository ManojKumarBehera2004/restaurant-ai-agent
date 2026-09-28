"""
Embedding Service Module.
Provides vector embeddings with Gemini API support and a deterministic TF-IDF semantic model.
"""

import math
import hashlib
import re
from typing import List, Dict
from app.core.config import settings
from app.core.logging import logger

try:
    import google.generativeai as gai
except ImportError:
    gai = None


STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "is", "are", "was", "were",
    "in", "on", "at", "to", "for", "with", "about", "by", "of", "from",
    "can", "could", "should", "would", "what", "where", "how", "when", "why",
    "my", "your", "our", "their", "it", "this", "that", "these", "those", "i", "me"
}


class BaseEmbeddingService:
    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_documents(self, docs: List[str]) -> List[List[float]]:
        return [self.embed_text(doc) for doc in docs]


class LocalDeterministicEmbeddingService(BaseEmbeddingService):
    """
    Deterministic TF-IDF hash vector embedding for offline/testing scenarios.
    Uses SHA-256 for stable, cross-process hash projection with term weighting.
    """
    def __init__(self, dimension: int = 512):
        self.dimension = dimension

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        tokens = [w for w in cleaned.split() if w and len(w) > 1 and w not in STOPWORDS]
        return tokens

    def _stable_hash(self, text: str, salt: str = "") -> int:
        key = (text + salt).encode("utf-8")
        return int(hashlib.sha256(key).hexdigest()[:8], 16)

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        tokens = self._tokenize(text)
        vector = [0.0] * self.dimension

        if not tokens:
            return [0.0] * self.dimension

        freqs: Dict[str, int] = {}
        for t in tokens:
            freqs[t] = freqs.get(t, 0) + 1

        for token, count in freqs.items():
            h1 = self._stable_hash(token) % self.dimension
            h2 = self._stable_hash(token, "_alt") % self.dimension
            weight = 1.0 + math.log(float(count))
            vector[h1] += 3.0 * weight
            vector[h2] += 1.5 * weight

        # Add Bigrams with heavy context weight
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            hb = self._stable_hash(bigram, "_bi") % self.dimension
            vector[hb] += 5.0

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector


class GeminiEmbeddingService(BaseEmbeddingService):
    """Embeddings generated via Google Gemini API."""
    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        self.api_key = api_key
        self.model = model
        if gai:
            gai.configure(api_key=api_key)

    def embed_text(self, text: str) -> List[float]:
        if not gai or not self.api_key:
            return LocalDeterministicEmbeddingService().embed_text(text)
        try:
            result = gai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_query"
            )
            return result["embedding"]
        except Exception as e:
            logger.warning(f"Gemini embedding API failed ({e}). Falling back to local embedding.")
            return LocalDeterministicEmbeddingService().embed_text(text)


def is_valid_api_key(key: str) -> bool:
    if not key or not isinstance(key, str):
        return False
    cleaned = key.strip().lower()
    return bool(cleaned and not any(p in cleaned for p in ["your-", "your_", "placeholder", "key_here", "example"]))


def get_embedding_service() -> BaseEmbeddingService:
    """Factory to get the appropriate embedding service based on settings."""
    if is_valid_api_key(settings.GEMINI_API_KEY) and gai:
        return GeminiEmbeddingService(api_key=settings.GEMINI_API_KEY)
    return LocalDeterministicEmbeddingService()


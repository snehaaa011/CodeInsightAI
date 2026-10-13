"""
CodeInsight AI - Embedding Generation
NEW (CodeInsight AI): pluggable embedding provider.
Default: local sentence-transformers model (no API key required, ideal for an
academic demo). Optional: OpenAI embeddings if EMBEDDING_PROVIDER=openai.
"""
from typing import List
from ..config import settings

_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(settings.embedding_model)
    return _local_model


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    if settings.embedding_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [d.embedding for d in resp.data]
    # default: local
    model = _get_local_model()
    return model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]

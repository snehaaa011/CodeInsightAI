"""
CodeInsight AI - Vector Store
NEW (CodeInsight AI): ChromaDB-backed persistent vector store used for
semantic retrieval over code chunks. One Chroma collection per repository.
"""
from typing import List, Dict, Any
import chromadb
from ..config import settings
from .embeddings import embed_texts, embed_text
from .chunker import Chunk

_client = chromadb.PersistentClient(path=settings.vector_store_dir)


def _collection_name(repo_id: str) -> str:
    return f"repo_{repo_id}".replace("-", "_")


def get_or_create_collection(repo_id: str):
    return _client.get_or_create_collection(name=_collection_name(repo_id))


def index_chunks(repo_id: str, chunks: List[Chunk], batch_size: int = 64) -> int:
    collection = get_or_create_collection(repo_id)
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embeddings = embed_texts([c.text for c in batch])
        collection.add(
            ids=[c.id for c in batch],
            embeddings=embeddings,
            documents=[c.text for c in batch],
            metadatas=[{
                "file_path": c.file_path,
                "entity_id": c.entity_id,
                "entity_name": c.entity_name,
                "entity_type": c.entity_type,
                "language": c.language,
                "start_line": c.start_line,
                "end_line": c.end_line,
            } for c in batch]
        )
        total += len(batch)
    return total


def query(repo_id: str, question: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or settings.top_k_vector
    collection = get_or_create_collection(repo_id)
    if collection.count() == 0:
        return []
    query_embedding = embed_text(question)
    results = collection.query(query_embeddings=[query_embedding], n_results=min(top_k, collection.count()))
    output = []
    for doc, meta, dist, _id in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0], results["ids"][0]
    ):
        output.append({
            "id": _id, "text": doc, "metadata": meta,
            "score": 1 - dist,  # cosine distance -> similarity-ish score
        })
    return output


def collection_size(repo_id: str) -> int:
    return get_or_create_collection(repo_id).count()


def delete_repo_collection(repo_id: str):
    try:
        _client.delete_collection(_collection_name(repo_id))
    except Exception:
        pass

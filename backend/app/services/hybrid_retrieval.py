"""
CodeInsight AI - Hybrid Retrieval
NEW (CodeInsight AI): the core academic contribution requested by the brief -
combines Vector Store semantic search with Knowledge Graph structural
traversal so answers are grounded in both "what looks similar" (embeddings)
and "what is actually connected" (CALLS / EXTENDS / IMPLEMENTS / CONTAINS).
"""
from typing import List, Dict, Any
from . import vector_store, graph_store


def hybrid_retrieve(repo_id: str, question: str) -> Dict[str, Any]:
    # 1. Vector retrieval: semantically similar code chunks
    vector_hits = vector_store.query(repo_id, question)

    # 2. Graph retrieval: structurally related entities, seeded from the
    #    vector hits (their entity ids / file paths)
    seed_names = [h["metadata"]["entity_name"] for h in vector_hits]
    seed_files = [h["metadata"]["file_path"] for h in vector_hits]
    seed_ids = graph_store.find_entity_ids_by_name_or_file(repo_id, seed_names, seed_files)
    graph_hits = graph_store.expand_neighbors(repo_id, seed_ids) if seed_ids else []

    return {"vector_hits": vector_hits, "graph_hits": graph_hits}


def build_context_and_sources(retrieval: Dict[str, Any]):
    """Builds the LLM context string and a de-duplicated list of source records."""
    context_parts = []
    sources = []
    seen_files = set()

    for hit in retrieval["vector_hits"]:
        meta = hit["metadata"]
        context_parts.append(hit["text"])
        key = (meta["file_path"], meta["entity_name"])
        if key not in seen_files:
            seen_files.add(key)
            sources.append({
                "file_path": meta["file_path"],
                "entity_name": meta["entity_name"],
                "entity_type": meta["entity_type"],
                "start_line": meta["start_line"],
                "end_line": meta["end_line"],
                "snippet": hit["text"][:400],
                "retrieval_type": "vector",
            })

    if retrieval["graph_hits"]:
        graph_summary_lines = ["\nStructurally related entities (from the code knowledge graph):"]
        for g in retrieval["graph_hits"]:
            graph_summary_lines.append(
                f"- {g.get('type')} `{g.get('name')}` in {g.get('file_path')} "
                f"(lines {g.get('start_line')}-{g.get('end_line')})"
            )
            key = (g.get("file_path"), g.get("name"))
            if key not in seen_files:
                seen_files.add(key)
                sources.append({
                    "file_path": g.get("file_path"),
                    "entity_name": g.get("name"),
                    "entity_type": g.get("type"),
                    "start_line": g.get("start_line"),
                    "end_line": g.get("end_line"),
                    "snippet": g.get("signature") or "",
                    "retrieval_type": "graph",
                })
        context_parts.append("\n".join(graph_summary_lines))

    context = "\n\n".join(context_parts)
    return context, sources

"""
CodeInsight AI - Repository Analysis Orchestrator
NEW (CodeInsight AI): runs the full ingestion pipeline (clone -> parse ->
chunk -> embed -> index -> build graph) and tracks progress in SQLite so the
frontend can poll status (section 5 workflow, section 22 UI).
"""
from collections import Counter
from . import repo_ingestion, code_parser, chunker, vector_store, graph_store
from ..db import sqlite_store


def run_analysis(repo_id: str, repo_url: str, branch: str = None):
    try:
        sqlite_store.upsert_repo(repo_id, repo_url, status="cloning", progress=5, detail="Cloning repository...")
        local_path = repo_ingestion.clone_repo(repo_url, repo_id, branch)
        repo_name = repo_ingestion.repo_name_from_url(repo_url)
        sqlite_store.upsert_repo(repo_id, repo_url, repo_name=repo_name)

        sqlite_store.upsert_repo(repo_id, repo_url, status="parsing", progress=25, detail="Discovering & parsing source files...")
        files = repo_ingestion.discover_source_files(local_path)
        if not files:
            raise repo_ingestion.RepoIngestionError(
                "No supported source files found (.py, .js, .jsx, .ts, .tsx, .java)."
            )

        all_entities = []
        language_counts = Counter()
        for abs_path, rel_path, language in files:
            entities = code_parser.parse_file(abs_path, rel_path, language)
            all_entities.extend(entities)
            language_counts[language] += 1

        sqlite_store.upsert_repo(repo_id, repo_url, status="embedding", progress=55, detail="Chunking & generating embeddings...")
        chunks = chunker.build_chunks(all_entities)
        vector_store.delete_repo_collection(repo_id)
        indexed = vector_store.index_chunks(repo_id, chunks)

        sqlite_store.upsert_repo(repo_id, repo_url, status="graphing", progress=80, detail="Building knowledge graph...")
        graph_store.build_graph(repo_id, all_entities)
        stats = graph_store.get_stats(repo_id)

        overview = {
            "repo_name": repo_name,
            "languages": dict(language_counts),
            "num_files": len(files),
            "num_classes": stats["num_classes"],
            "num_functions": stats["num_functions"],
            "num_relationships": stats["num_relationships"],
            "graph_status": graph_store.backend_name(),
            "vector_status": f"{indexed} chunks indexed",
        }
        sqlite_store.upsert_repo(repo_id, repo_url, status="ready", progress=100,
                                  detail="Repository analyzed successfully.", overview=overview)

    except repo_ingestion.RepoIngestionError as e:
        sqlite_store.upsert_repo(repo_id, repo_url, status="failed", progress=0, detail=str(e))
    except Exception as e:
        sqlite_store.upsert_repo(repo_id, repo_url, status="failed", progress=0,
                                  detail=f"Unexpected error during analysis: {e}")

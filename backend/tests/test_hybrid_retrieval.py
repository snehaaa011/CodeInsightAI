import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
from app.services import hybrid_retrieval


FAKE_VECTOR_HITS = [
    {
        "id": "c1", "text": "[python] Method `login` in auth.py (lines 1-5)\ndef login(...): ...",
        "metadata": {"file_path": "auth.py", "entity_id": "e1", "entity_name": "login",
                      "entity_type": "Method", "language": "python", "start_line": 1, "end_line": 5},
        "score": 0.9,
    }
]
FAKE_GRAPH_HITS = [
    {"id": "e2", "name": "check", "file_path": "auth.py", "start_line": 20, "end_line": 25,
     "type": "Method", "signature": "def check(...):"}
]


@patch("app.services.hybrid_retrieval.graph_store.expand_neighbors", return_value=FAKE_GRAPH_HITS)
@patch("app.services.hybrid_retrieval.graph_store.find_entity_ids_by_name_or_file", return_value={"e1"})
@patch("app.services.hybrid_retrieval.vector_store.query", return_value=FAKE_VECTOR_HITS)
def test_hybrid_retrieve_combines_vector_and_graph(mock_query, mock_find, mock_expand):
    result = hybrid_retrieval.hybrid_retrieve("repo-1", "Explain the login process")
    assert result["vector_hits"] == FAKE_VECTOR_HITS
    assert result["graph_hits"] == FAKE_GRAPH_HITS


def test_build_context_and_sources_deduplicates_and_labels_retrieval_type():
    retrieval = {"vector_hits": FAKE_VECTOR_HITS, "graph_hits": FAKE_GRAPH_HITS}
    context, sources = hybrid_retrieval.build_context_and_sources(retrieval)
    assert "login" in context
    kinds = {s["retrieval_type"] for s in sources}
    assert kinds == {"vector", "graph"}
    assert len(sources) == 2

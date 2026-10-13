import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
from app.services import rag_pipeline

FAKE_RETRIEVAL = {
    "vector_hits": [{
        "id": "c1", "text": "def login(user, password):\n    return AuthService.check(user, password)",
        "metadata": {"file_path": "auth.py", "entity_id": "e1", "entity_name": "login",
                      "entity_type": "Method", "language": "python", "start_line": 1, "end_line": 3},
        "score": 0.95,
    }],
    "graph_hits": [],
}


@patch("app.services.rag_pipeline.llm_service.generate_answer",
       return_value="The login method calls AuthService.check to validate credentials.")
@patch("app.services.rag_pipeline.hybrid_retrieval.hybrid_retrieve", return_value=FAKE_RETRIEVAL)
def test_answer_question_returns_full_result(mock_retrieve, mock_llm):
    result = rag_pipeline.answer_question("repo-e2e", "How does login work?")
    assert "AuthService" in result["answer"]
    assert len(result["sources"]) == 1
    assert result["sources"][0]["file_path"] == "auth.py"
    v = result["verification"]
    assert 0.0 <= v["faithfulness"] <= 1.0
    assert 0.0 <= v["answer_relevancy"] <= 1.0
    assert v["response_time_seconds"] >= 0
    assert result["answer_id"]

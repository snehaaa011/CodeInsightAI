import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Uses the project's default ./data/codeinsight.db (created automatically).
# Unique repo/answer ids below keep this test independent of other runs.
from app.db import sqlite_store


def test_upsert_and_get_repo():
    sqlite_store.upsert_repo("repo-x", "https://github.com/a/b", status="queued", progress=0, detail="q")
    repo = sqlite_store.get_repo("repo-x")
    assert repo["status"] == "queued"
    sqlite_store.upsert_repo("repo-x", "https://github.com/a/b", status="ready", progress=100)
    repo = sqlite_store.get_repo("repo-x")
    assert repo["status"] == "ready"
    assert repo["progress"] == 100


def test_save_and_get_answer_and_feedback():
    sqlite_store.upsert_repo("repo-y", "https://github.com/a/c", status="ready", progress=100)
    sqlite_store.save_answer("ans-1", "repo-y", "What does this do?", "It does X.",
                              [{"file_path": "a.py"}], 0.9, 0.8, 1.2)
    answer = sqlite_store.get_answer("ans-1")
    assert answer["question"] == "What does this do?"

    sqlite_store.save_feedback("ans-1", True)
    sqlite_store.save_feedback("ans-1", False)
    helpful, not_helpful = sqlite_store.feedback_counts_for_repo("repo-y")
    assert helpful == 1
    assert not_helpful == 1

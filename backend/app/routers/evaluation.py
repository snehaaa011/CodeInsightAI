"""
CodeInsight AI - Evaluation dashboard endpoint (section 25)
NEW (CodeInsight AI)
"""
import json
from fastapi import APIRouter, HTTPException
from ..models.schemas import EvaluationSummary
from ..db import sqlite_store

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/{repo_id}/summary", response_model=EvaluationSummary)
def evaluation_summary(repo_id: str):
    repo = sqlite_store.get_repo(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    answers = sqlite_store.list_answers_for_repo(repo_id)
    n = len(answers)
    avg_faith = round(sum(a["faithfulness"] for a in answers) / n, 4) if n else 0.0
    avg_rel = round(sum(a["answer_relevancy"] for a in answers) / n, 4) if n else 0.0
    avg_time = round(sum(a["response_time"] for a in answers) / n, 3) if n else 0.0
    helpful, not_helpful = sqlite_store.feedback_counts_for_repo(repo_id)

    repo_name = repo["repo_name"] or repo_id
    return EvaluationSummary(
        repo_id=repo_id, repo_name=repo_name, questions_tested=n,
        avg_faithfulness=avg_faith, avg_answer_relevancy=avg_rel, avg_response_time=avg_time,
        helpful_count=helpful, not_helpful_count=not_helpful
    )


@router.get("/{repo_id}/answers")
def list_answers(repo_id: str):
    answers = sqlite_store.list_answers_for_repo(repo_id)
    for a in answers:
        a["sources_json"] = json.loads(a["sources_json"]) if a["sources_json"] else []
    return answers

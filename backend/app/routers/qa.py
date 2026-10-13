"""
CodeInsight AI - Q&A endpoints
NEW (CodeInsight AI)
"""
from fastapi import APIRouter, HTTPException
from ..models.schemas import AskRequest, AskResponse
from ..services import rag_pipeline
from ..db import sqlite_store

router = APIRouter(prefix="/api/qa", tags=["qa"])


@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    repo = sqlite_store.get_repo(req.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found. Analyze it first.")
    if repo["status"] != "ready":
        raise HTTPException(status_code=409, detail=f"Repository is not ready yet (status: {repo['status']}).")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = rag_pipeline.answer_question(req.repo_id, req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate an answer: {e}")

    return result

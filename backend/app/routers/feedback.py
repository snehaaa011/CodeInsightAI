"""
CodeInsight AI - Feedback endpoint (section 21)
NEW (CodeInsight AI)
"""
from fastapi import APIRouter, HTTPException
from ..models.schemas import FeedbackRequest
from ..db import sqlite_store

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("")
def submit_feedback(req: FeedbackRequest):
    existing = sqlite_store.get_answer(req.answer_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Answer not found.")
    sqlite_store.save_feedback(req.answer_id, req.helpful, req.comment)
    return {"message": "Feedback recorded. Thank you!"}

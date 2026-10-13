"""
CodeInsight AI - Repository endpoints
NEW (CodeInsight AI)
"""
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException
from ..models.schemas import AnalyzeRepoRequest, AnalyzeRepoResponse, RepoStatus, RepoOverview
from ..services import repo_ingestion, repo_analysis
from ..db import sqlite_store

router = APIRouter(prefix="/api/repository", tags=["repository"])


@router.post("/analyze", response_model=AnalyzeRepoResponse)
def analyze_repository(req: AnalyzeRepoRequest, background_tasks: BackgroundTasks):
    if not req.repo_url or "github.com" not in req.repo_url:
        raise HTTPException(status_code=400, detail="Please provide a valid GitHub repository URL.")

    repo_id = repo_ingestion.make_repo_id(req.repo_url)
    sqlite_store.upsert_repo(repo_id, req.repo_url, status="queued", progress=0, detail="Queued for analysis.")
    background_tasks.add_task(repo_analysis.run_analysis, repo_id, req.repo_url, req.branch)
    return AnalyzeRepoResponse(repo_id=repo_id, status="queued", message="Repository analysis started.")


@router.get("/{repo_id}/status", response_model=RepoStatus)
def get_status(repo_id: str):
    repo = sqlite_store.get_repo(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return RepoStatus(repo_id=repo_id, status=repo["status"], progress=repo["progress"], detail=repo["detail"])


@router.get("/{repo_id}/overview", response_model=RepoOverview)
def get_overview(repo_id: str):
    repo = sqlite_store.get_repo(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo["status"] != "ready" or not repo["overview_json"]:
        raise HTTPException(status_code=409, detail=f"Repository is not ready yet (status: {repo['status']}).")
    overview = json.loads(repo["overview_json"])
    return RepoOverview(repo_id=repo_id, **overview)


@router.get("/list")
def list_repositories():
    return sqlite_store.list_repos()

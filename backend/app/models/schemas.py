"""
CodeInsight AI - API data models (Pydantic schemas)
NEW (CodeInsight AI)
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AnalyzeRepoRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repository URL")
    branch: Optional[str] = Field(None, description="Branch to analyze (default: repo default branch)")


class AnalyzeRepoResponse(BaseModel):
    repo_id: str
    status: str
    message: str


class RepoStatus(BaseModel):
    repo_id: str
    status: str  # queued | cloning | parsing | embedding | graphing | ready | failed
    progress: int
    detail: str = ""


class RepoOverview(BaseModel):
    repo_id: str
    repo_name: str
    languages: Dict[str, int]
    num_files: int
    num_classes: int
    num_functions: int
    num_relationships: int
    graph_status: str
    vector_status: str


class AskRequest(BaseModel):
    repo_id: str
    question: str


class RetrievedSource(BaseModel):
    file_path: str
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    snippet: str
    retrieval_type: str  # "vector" | "graph"


class VerificationResult(BaseModel):
    faithfulness: float
    answer_relevancy: float
    response_time_seconds: float
    faithfulness_method: str
    relevancy_method: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[RetrievedSource]
    verification: VerificationResult
    answer_id: str


class FeedbackRequest(BaseModel):
    answer_id: str
    helpful: bool
    comment: Optional[str] = None


class EvaluationSummary(BaseModel):
    repo_id: str
    repo_name: str
    questions_tested: int
    avg_faithfulness: float
    avg_answer_relevancy: float
    avg_response_time: float
    helpful_count: int
    not_helpful_count: int

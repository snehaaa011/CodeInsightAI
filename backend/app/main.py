"""
CodeInsight AI - Application Entrypoint
NEW (CodeInsight AI): FastAPI app wiring all routers together and serving
the static frontend.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from .config import settings
from .routers import repository, qa, feedback, evaluation

app = FastAPI(
    title="CodeInsight AI",
    description="Intelligent Software Repository Analysis Using RAG "
                 "(academic project extending CodeRAG's graph-based code intelligence "
                 "with hybrid RAG Q&A and an AI Response Verification module).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repository.router)
app.include_router(qa.router)
app.include_router(feedback.router)
app.include_router(evaluation.router)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # section 28: never leak stack traces to the user
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred. Please try again."})


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

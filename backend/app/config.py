"""
CodeInsight AI - Configuration
NEW (CodeInsight AI): centralised, environment-driven configuration for every
component of the pipeline (repo ingestion, graph, vector store, LLM, verification).
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # --- General ---
    app_name: str = "CodeInsight AI"
    data_dir: str = os.getenv("DATA_DIR", "./data")
    workspace_dir: str = os.getenv("WORKSPACE_DIR", "./data/repos")

    # --- LLM provider: "anthropic" | "openai" | "gemini" | "mock" ---
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv(
        "ANTHROPIC_MODEL",
        "claude-sonnet-4-6"
    )

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv(
        "OPENAI_MODEL",
        "gpt-4o-mini"
    )

    # Google Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    # Maximum output tokens for LLM responses
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "800"))

    # --- Embeddings ---
    embedding_provider: str = os.getenv(
        "EMBEDDING_PROVIDER",
        "local"
    )  # local | openai

    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "all-MiniLM-L6-v2"
    )

    # --- Vector store (Chroma, local & persistent) ---
    vector_store_dir: str = os.getenv(
        "VECTOR_STORE_DIR",
        "./data/vector_store"
    )

    # --- Knowledge graph ---
    graph_backend: str = os.getenv(
        "GRAPH_BACKEND",
        "neo4j"
    )  # neo4j | networkx

    neo4j_uri: str = os.getenv(
        "NEO4J_URI",
        "bolt://localhost:7687"
    )

    neo4j_user: str = os.getenv(
        "NEO4J_USER",
        "neo4j"
    )

    neo4j_password: str = os.getenv(
        "NEO4J_PASSWORD",
        "password"
    )

    # --- Chunking ---
    chunk_max_lines: int = int(
        os.getenv("CHUNK_MAX_LINES", "60")
    )

    chunk_overlap_lines: int = int(
        os.getenv("CHUNK_OVERLAP_LINES", "5")
    )

    # --- Retrieval ---
    top_k_vector: int = int(
        os.getenv("TOP_K_VECTOR", "6")
    )

    graph_hops: int = int(
        os.getenv("GRAPH_HOPS", "2")
    )

    # --- App server ---
    host: str = os.getenv(
        "HOST",
        "0.0.0.0"
    )

    port: int = int(
        os.getenv("PORT", "8000")
    )

    cors_origins: list = field(
        default_factory=lambda: ["*"]
    )

    supported_extensions: dict = field(
        default_factory=lambda: {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
        }
    )


settings = Settings()

os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(settings.workspace_dir, exist_ok=True)
os.makedirs(settings.vector_store_dir, exist_ok=True)
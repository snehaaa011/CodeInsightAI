"""
CodeInsight AI - Repository Ingestion
NEW (CodeInsight AI): clones a public GitHub repository and discovers
source files of supported languages. (CodeRAG instead analyzes remote repos
via API without local cloning; we use local shallow clone for simplicity,
which is a documented, deliberate scope reduction for this academic project.)
"""
import os
import re
import shutil
import subprocess
import uuid
from typing import List, Tuple
from ..config import settings

IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    "target", ".idea", ".vscode", "vendor", "coverage", ".mypy_cache", "egg-info"
}


class RepoIngestionError(Exception):
    pass


def make_repo_id(repo_url: str) -> str:
    name = re.sub(r'[^a-zA-Z0-9]+', '-', repo_url.rstrip("/").split("/")[-1])
    return f"{name}-{uuid.uuid4().hex[:6]}".lower()


def clone_repo(repo_url: str, repo_id: str, branch: str = None) -> str:
    if not re.match(r'^https?://', repo_url):
        raise RepoIngestionError("Invalid repository URL. Must start with http:// or https://")

    dest = os.path.join(settings.workspace_dir, repo_id)
    if os.path.exists(dest):
        shutil.rmtree(dest)

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [repo_url, dest]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise RepoIngestionError("Repository clone timed out.")
    except FileNotFoundError:
        raise RepoIngestionError("git is not installed on this server.")

    if result.returncode != 0:
        raise RepoIngestionError(f"Unable to clone repository: {result.stderr.strip()[:400]}")

    return dest


def discover_source_files(root_dir: str) -> List[Tuple[str, str, str]]:
    """Returns list of (absolute_path, relative_path, language)."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            language = settings.supported_extensions.get(ext)
            if language:
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_path, root_dir)
                files.append((abs_path, rel_path, language))
    return files


def repo_name_from_url(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")

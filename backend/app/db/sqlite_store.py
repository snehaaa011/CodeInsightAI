"""
CodeInsight AI - Lightweight SQLite persistence
NEW (CodeInsight AI): stores repo metadata/status, Q&A answer log (for feedback
linkage) and evaluation results. Kept deliberately simple (no ORM) per the
"do not overcomplicate" scope of the project.
"""
import sqlite3
import json
import threading
from contextlib import contextmanager
from ..config import settings

DB_PATH = f"{settings.data_dir}/codeinsight.db"
_lock = threading.Lock()


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            repo_id TEXT PRIMARY KEY,
            repo_url TEXT,
            repo_name TEXT,
            status TEXT,
            progress INTEGER,
            detail TEXT,
            overview_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            answer_id TEXT PRIMARY KEY,
            repo_id TEXT,
            question TEXT,
            answer TEXT,
            sources_json TEXT,
            faithfulness REAL,
            answer_relevancy REAL,
            response_time REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_id TEXT,
            helpful INTEGER,
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


_init_db()


@contextmanager
def get_conn():
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


# ---------- Repository ----------

def upsert_repo(repo_id, repo_url, repo_name=None, status=None, progress=None, detail=None, overview=None):
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM repositories WHERE repo_id=?", (repo_id,)).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO repositories (repo_id, repo_url, repo_name, status, progress, detail, overview_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (repo_id, repo_url, repo_name or "", status or "queued", progress or 0, detail or "",
                 json.dumps(overview) if overview else None)
            )
        else:
            fields, values = [], []
            if repo_name is not None:
                fields.append("repo_name=?"); values.append(repo_name)
            if status is not None:
                fields.append("status=?"); values.append(status)
            if progress is not None:
                fields.append("progress=?"); values.append(progress)
            if detail is not None:
                fields.append("detail=?"); values.append(detail)
            if overview is not None:
                fields.append("overview_json=?"); values.append(json.dumps(overview))
            if fields:
                values.append(repo_id)
                conn.execute(f"UPDATE repositories SET {', '.join(fields)} WHERE repo_id=?", values)


def get_repo(repo_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM repositories WHERE repo_id=?", (repo_id,)).fetchone()
        return dict(row) if row else None


def list_repos():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM repositories ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# ---------- Answers ----------

def save_answer(answer_id, repo_id, question, answer, sources, faithfulness, relevancy, response_time):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO answers (answer_id, repo_id, question, answer, sources_json, faithfulness, "
            "answer_relevancy, response_time) VALUES (?,?,?,?,?,?,?,?)",
            (answer_id, repo_id, question, answer, json.dumps(sources), faithfulness, relevancy, response_time)
        )


def get_answer(answer_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM answers WHERE answer_id=?", (answer_id,)).fetchone()
        return dict(row) if row else None


def list_answers_for_repo(repo_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM answers WHERE repo_id=?", (repo_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------- Feedback ----------

def save_feedback(answer_id, helpful, comment=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO feedback (answer_id, helpful, comment) VALUES (?,?,?)",
            (answer_id, 1 if helpful else 0, comment)
        )


def feedback_counts_for_repo(repo_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT f.helpful, COUNT(*) as cnt FROM feedback f
            JOIN answers a ON a.answer_id = f.answer_id
            WHERE a.repo_id = ?
            GROUP BY f.helpful
        """, (repo_id,)).fetchall()
        helpful = sum(r["cnt"] for r in rows if r["helpful"] == 1)
        not_helpful = sum(r["cnt"] for r in rows if r["helpful"] == 0)
        return helpful, not_helpful

# CodeInsight AI — How To Run The Full Project

Follow these steps in order. Two run modes are supported:

- **Mode A — Fastest demo (no Neo4j, no API key)**: uses the NetworkX graph
  fallback and the offline mock LLM. Good for a first smoke-test.
- **Mode B — Full setup (Neo4j + a real LLM)**: matches the brief exactly
  (real knowledge graph in Neo4j, real LLM-generated answers).

Both modes use the same code; you only change values in `.env`.

---

## 0. Prerequisites

- Python 3.10+ (`python3 --version`)
- `git` installed and on your PATH
- (Mode B only) Docker Desktop, **or** a Neo4j instance you already run
- (Mode B only) An Anthropic or OpenAI API key
- Internet access (needed to `pip install`, to `git clone` the repositories
  you'll analyze, and — the first time only — to download the local
  embedding model `all-MiniLM-L6-v2`, ~90MB)

---

## 1. Get the project onto your machine

Unzip/copy the `CodeInsightAI/` folder anywhere, then open a terminal there:

```bash
cd CodeInsightAI
```

## 2. Create a Python virtual environment and install dependencies

```bash
cd backend
python3 -m venv venv

# Activate it:
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows (PowerShell/cmd)

pip install --upgrade pip
pip install -r requirements.txt
```

This installs FastAPI, ChromaDB, sentence-transformers, the neo4j driver,
networkx, anthropic, openai, pytest, etc.

> If `pip install` fails on `sentence-transformers` due to `torch`, install
> a CPU-only torch build first: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
> then re-run `pip install -r requirements.txt`.

## 3. Configure environment variables

```bash
cp .env.example .env       # macOS / Linux
copy .env.example .env     # Windows
```

Open `backend/.env` in an editor.

### Mode A — Fastest demo (no external services)
Leave these as-is (already the defaults):
```
LLM_PROVIDER=mock
GRAPH_BACKEND=neo4j     # change this one line ↓
```
Change just one line so it doesn't try to reach a real Neo4j server:
```
GRAPH_BACKEND=networkx
```
That's it — skip to Step 5.

### Mode B — Full setup

**3.1 Start Neo4j** (pick one):

- **Docker (recommended)** — from the project root (one level up from `backend/`):
  ```bash
  cd ..
  docker compose up -d
  cd backend
  ```
  This starts Neo4j on `bolt://localhost:7687` with user `neo4j` / password `password`
  (matching `.env.example`), and a browser UI at http://localhost:7474.

- **Or** point `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` in `.env` at any
  Neo4j instance you already have running (local install or Neo4j Aura).

Keep `GRAPH_BACKEND=neo4j` in `.env`.

**3.2 Configure a real LLM** — edit `.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...your key...
```
or
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...your key...
```

## 4. (Optional) Run the automated tests

From the `backend/` folder, with the virtual environment active:

```bash
pytest tests/ -v
```

All tests should pass. (`test_qa_pipeline.py` and `test_verification.py`
will download the local embedding model on first run if you haven't already
— this needs internet access once.)

## 5. Start the backend server

From the `backend/` folder:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see Uvicorn start and log `Application startup complete.`

Leave this terminal running.

## 6. Open the app

Open your browser at:

```
http://localhost:8000
```

The frontend (Dashboard / Ask a Question / Evaluation tabs) is served
directly by the backend — no separate frontend server needed.

You can also check the interactive API docs at:
```
http://localhost:8000/docs
```

## 7. Use the app

1. **Dashboard tab** → paste a public GitHub repo URL, e.g.
   `https://github.com/psf/requests`, and click **Analyze Repository**.
   Watch the progress bar (cloning → parsing → embedding → graphing → ready).
2. Once ready, the **Repository Overview** card shows file/class/function/
   relationship counts and which graph backend/vector store were used.
3. **Ask a Question tab** → type a question, e.g. *"Where is user
   authentication implemented?"* and click **Ask**. You'll see:
   - the generated answer,
   - **Retrieved Sources** (files/entities, tagged `vector` or `graph`),
   - **AI Response Verification** (Faithfulness %, Answer Relevancy %,
     Response Time),
   - 👍 / 👎 feedback buttons.
4. **Evaluation tab** → click **Refresh** to see aggregate metrics across
   all the questions you've asked for the active repository.

> Tip: start with a small-to-medium repository the first time — analysis
> time depends on repository size (cloning + parsing + embedding every file).

## 8. Run the full curated evaluation (section 24 of the brief)

With the backend still running in another terminal:

```bash
cd CodeInsightAI          # project root
pip install requests      # only needed once, for the evaluation script
python evaluation/run_evaluation.py
```

This analyzes each repository listed in `evaluation/dataset.json`, asks all
its questions through the real API, and writes real measured results to
`evaluation/results.json`. Edit `dataset.json` to use different repositories
or questions.

## 9. Stopping everything

- Stop the backend: `Ctrl+C` in its terminal.
- Stop Neo4j (Mode B, Docker): `docker compose down` (add `-v` to also wipe
  the graph data volume).

## 10. Common problems (section 28 error handling)

| Symptom | Likely cause / fix |
|---|---|
| "Please provide a valid GitHub repository URL" | URL must contain `github.com` and start with `http(s)://` |
| Analysis status stays `failed` with a git error | Repository is private/doesn't exist, or `git` isn't installed |
| Overview shows `networkx (fallback - Neo4j unavailable)` even with `GRAPH_BACKEND=neo4j` | Neo4j isn't reachable — check `docker compose ps` / your `NEO4J_URI`, user, password |
| Answers say `[Mock LLM - no LLM_PROVIDER configured]` | Set `LLM_PROVIDER` and the matching API key in `.env`, then restart uvicorn |
| `LLM generation failed: ANTHROPIC_API_KEY is not configured.` | Add a real key to `.env` and restart the server |
| First request is slow | The local embedding model downloads once (~90MB) and loads into memory on first use |
| `ModuleNotFoundError` on startup | You forgot to activate the virtual environment, or `pip install -r requirements.txt` didn't finish successfully |

# CodeInsight AI
### Intelligent Software Repository Analysis Using RAG
*An MCA Major Project — Artificial Intelligence · Retrieval-Augmented Generation · Knowledge Graphs · Vector Databases · Software Engineering · Explainable AI*

CodeInsight AI lets a user paste a public GitHub repository URL and then ask
natural-language questions about it ("Explain the login process", "Where is
authentication implemented?") and get an answer that is:

- **Grounded** in the actual retrieved source code (vector search + a Neo4j
  knowledge graph of code structure),
- **Explainable** (every answer shows exactly which files/entities it came from),
- **Verified** (Faithfulness, Answer Relevancy, Response Time, and User
  Feedback are shown alongside every answer — the "AI Response
  Verification" module).

➡️ **To run the project, see [`RUN_INSTRUCTIONS.md`](./RUN_INSTRUCTIONS.md).**

---

## 1. Relationship to the base project (CodeRAG)

This project is built **on top of the concepts** of the open-source project
[CodeRAG](https://github.com/JonnoC/CodeRAG) (a Neo4j-based, TypeScript code
intelligence MCP server). CodeInsight AI is **not** a re-skin of CodeRAG —
it reuses CodeRAG's graph schema and choice of Neo4j, and builds an entirely
new RAG/Q&A/verification layer on top, which is exactly what CodeRAG itself
does not provide.

Because the sandboxed environment used to build this submission had no
outbound internet access for cloning/inspecting the CodeRAG TypeScript
source, its documented public README/architecture (retrieved via web
search) was used as the reference instead of the literal source tree. **This
is explained in full, with an honest existing/modified/new breakdown, in
[`docs/contribution.md`](./docs/contribution.md)** — please read that file,
it is required reading for grading the "base project" requirement fairly.

## 2. What the system does (end to end)

```
User → paste GitHub URL → clone & parse code → build Neo4j graph
      → chunk & embed code → store in ChromaDB
      → user asks a question → hybrid (vector + graph) retrieval
      → LLM generates a grounded answer
      → AI Response Verification (Faithfulness / Relevancy / Time)
      → Answer + Sources + Verification shown in the UI
      → user gives 👍/👎 feedback
```

See [`docs/architecture.md`](./docs/architecture.md) for the full diagram
and a module-by-module explanation.

## 3. Project structure

```
CodeInsightAI/
├── README.md                     <- you are here
├── RUN_INSTRUCTIONS.md           <- step-by-step run guide (start here to run it)
├── docker-compose.yml            <- optional Neo4j container
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py               <- FastAPI entrypoint
│   │   ├── config.py             <- all configuration (env-driven)
│   │   ├── models/schemas.py     <- Pydantic request/response models
│   │   ├── services/             <- all pipeline logic (see architecture.md)
│   │   ├── routers/              <- REST API endpoints
│   │   └── db/sqlite_store.py    <- SQLite persistence
│   └── tests/                    <- pytest suite
├── frontend/                     <- static HTML/CSS/JS UI (served by FastAPI)
├── evaluation/
│   ├── dataset.json              <- curated repos + questions (section 23-24)
│   └── run_evaluation.py         <- reproducible evaluation script
└── docs/
    ├── architecture.md
    └── contribution.md           <- existing vs. modified vs. new (required reading)
```

## 4. Key design decisions (and why)

| Decision | Reason |
|---|---|
| Neo4j (with an automatic NetworkX in-process fallback) | Matches CodeRAG's graph DB choice, but the system still runs/demos with zero external services if Neo4j isn't available |
| ChromaDB (local, persistent, no server) | Zero-ops vector database, ideal for an academic demo |
| Local `sentence-transformers` embeddings by default | No API key required to run the whole pipeline |
| Pluggable LLM: Anthropic / OpenAI / offline "mock" | Same for the LLM — the system is demonstrable with `LLM_PROVIDER=mock` and no key at all |
| Faithfulness/Relevancy via embedding cosine similarity, with optional RAGAS | RAGAS's default metrics require an LLM judge (OpenAI); a real, non-fabricated, dependency-light alternative is used by default and documented in `services/verification.py` |
| Python `ast` for Python, regex heuristics for JS/TS/Java | Accurate parsing where possible, no native tree-sitter grammar builds required for the other languages (documented trade-off) |

## 5. Academic contribution summary (section 32 of the brief)

1. Natural-language repository Q&A
2. Hybrid Vector Store + Knowledge Graph retrieval
3. Explainable answers via retrieved source files
4. AI Response Verification (Faithfulness, Answer Relevancy, Response Time)
5. User Feedback capture and an evaluation dashboard

## 6. Security & configuration

- All secrets (LLM API keys, Neo4j credentials) are read from environment
  variables via `backend/.env` (see `backend/.env.example`). **Never commit
  a real `.env` file.**
- Errors (invalid repo URL, unreachable Neo4j, LLM failures, empty
  retrieval, etc.) are caught and shown as friendly messages — internal
  stack traces are never returned to the client (`app/main.py`'s global
  exception handler, plus explicit `try/except` in the ingestion pipeline).

## 7. License

This academic project inherits no code from CodeRAG's TypeScript source (it
was not accessible in this build environment, as documented above). All
Python/JS/HTML code here is original for this MCA project. CodeRAG itself
is MIT licensed — see https://github.com/JonnoC/CodeRAG.

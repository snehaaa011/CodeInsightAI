# CodeInsight AI — Architecture

```
USER
 |
 v
FRONTEND (static HTML/CSS/JS: Dashboard, Q&A, Evaluation)
 |
 v
FASTAPI BACKEND
 |
 v
REPOSITORY INGESTION  (git clone --depth 1, language-aware file discovery)
 |
 v
CODE ANALYSIS / PARSING (ast for Python; regex heuristics for JS/TS/Java)
 |
 +-------------------------------+
 |                               |
 v                               v
CODE CHUNKING -> EMBEDDINGS   KNOWLEDGE GRAPH BUILD
 |                               |
 v                               v
VECTOR STORE (ChromaDB)       NEO4J  (or NetworkX in-process fallback)
 |                               |
 +---------------+---------------+
                 v
          HYBRID RETRIEVAL
     (vector similarity + graph
      traversal seeded from hits)
                 v
          CONTEXT BUILDER
                 v
        LLM (Anthropic / OpenAI / offline mock)
                 v
          GENERATED ANSWER
                 v
     AI RESPONSE VERIFICATION MODULE
       +----------+----------+----------+
       |          |          |          |
  Faithfulness Relevancy  Response   User
  (embedding   (embedding  Time      Feedback
   cosine)      cosine)   (measured) (👍/👎)
                 v
       ANSWER + SOURCES + VERIFICATION
        (returned to frontend, logged to SQLite)
```

## Component notes

- **Repository ingestion** (`services/repo_ingestion.py`): shallow `git clone`
  of a public GitHub URL, then a directory walk that skips build/vendor
  folders and keeps only supported extensions (.py/.js/.jsx/.ts/.tsx/.java).
- **Code parsing** (`services/code_parser.py`): produces a language-agnostic
  `CodeEntity` (File/Class/Interface/Function/Method) with `calls`, `extends`,
  `implements`, `imports` — the same conceptual schema CodeRAG documents.
  Python uses the real `ast` module; other languages use documented regex
  heuristics (a deliberate scope reduction, see `docs/contribution.md`).
- **Chunking** (`services/chunker.py`): one chunk per entity, with a line-window
  overlap split for large bodies, so both a short method and a long class
  remain searchable.
- **Embeddings** (`services/embeddings.py`): local `sentence-transformers`
  by default (no API key needed); OpenAI embeddings optional.
- **Vector store** (`services/vector_store.py`): one persistent ChromaDB
  collection per repository.
- **Knowledge graph** (`services/graph_store.py`): Neo4j by default (matches
  CodeRAG's choice); automatically falls back to an in-process NetworkX graph
  if Neo4j is unreachable, so the system stays demonstrable offline.
- **Hybrid retrieval** (`services/hybrid_retrieval.py`): vector search finds
  semantically similar chunks; their entity/file identities seed a graph
  traversal (CONTAINS/CALLS/EXTENDS/IMPLEMENTS/DEFINED_IN, configurable hop
  count) so structurally connected code is pulled in even if it wasn't a top
  vector match.
- **RAG pipeline** (`services/rag_pipeline.py`): builds the prompt, calls the
  LLM, and times the whole request for the Response Time metric.
- **Verification module** (`services/verification.py`): Faithfulness and
  Answer Relevancy, computed from real embeddings every time (RAGAS used
  automatically if installed and an OpenAI key is configured; otherwise a
  documented local cosine-similarity method — never a hard-coded score).
- **Persistence** (`db/sqlite_store.py`): repository status, generated
  answers (for feedback linkage) and feedback, in a single SQLite file.

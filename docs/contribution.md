# CodeInsight AI — Relationship to the Base Project (CodeRAG)

This document exists to satisfy the brief's requirement to clearly separate
**existing base-project functionality**, **modified functionality**, and
**newly implemented functionality** — and to be transparent about a real
constraint encountered while building this academic project.

## What the actual base project is

The base project named in the brief, **JonnoC/CodeRAG**
(https://github.com/JonnoC/CodeRAG), is a **TypeScript/Node.js MCP
(Model Context Protocol) server** — not a Python web application. It:

- Is 98% TypeScript, with no existing Python backend, no existing web
  frontend, no existing vector database integration, and no existing
  LLM-based answer-generation pipeline.
- Parses TypeScript, JavaScript, Java and Python source into a **Neo4j**
  graph of code entities (File/Class/Interface/Method/Function) and
  relationships (CONTAINS/IMPORTS/CALLS/EXTENDS/IMPLEMENTS/DEFINED_IN).
- Exposes ~23 analysis tools over MCP to AI coding assistants (Claude Code,
  Cursor, Windsurf, GitHub Copilot), including a semantic-search tool backed
  by AI embeddings, and a CK-metrics/quality-assessment suite.
- Supports **remote** repository analysis (GitHub/GitLab/Bitbucket) via API,
  without local cloning.

## A documented constraint

This project was built in a sandboxed environment without outbound network
access from the code-execution runtime, so the actual CodeRAG TypeScript
source tree could not be cloned, inspected file-by-file, or literally
forked/modified here. Its public README and documentation pages were used
(via web search) to understand its architecture, schema, and scope.

Rather than fabricate a "modified CodeRAG" that never touched the real
source, **CodeInsight AI is presented honestly as a new implementation that:**

1. **Reuses CodeRAG's core concepts** — the same node/relationship schema for
   code structure, and Neo4j as the graph backend — so it is architecturally
   compatible with, and could in principle share a graph with, an actual
   CodeRAG deployment.
2. **Adds everything CodeRAG does not provide**, which is exactly the
   brief's required contribution: chunking, a vector store, hybrid
   vector+graph retrieval, an LLM-based natural-language Q&A layer,
   explainable source attribution, and the AI Response Verification module
   (Faithfulness, Answer Relevancy, Response Time, User Feedback).

If you have local access to the real CodeRAG source (e.g. by cloning it
yourself on a machine with internet access), the natural next step for a
stronger submission is to literally reuse its TypeScript parser/graph-writer
via its MCP tools (calling them from the Python backend as an MCP client)
instead of the regex/AST parser in `code_parser.py`. That integration point
is isolated to a single module, so it is a contained change.

## A. Existing CodeRAG functionality (conceptually reused)

| Concept | Where in CodeInsight AI |
|---|---|
| Neo4j as the graph database | `services/graph_store.py` |
| File/Class/Interface/Method/Function node schema | `services/code_parser.py`, `graph_store.py` |
| CONTAINS/IMPORTS/CALLS/EXTENDS/IMPLEMENTS/DEFINED_IN relationships | `graph_store.py` |
| Multi-language support (TS/JS/Java/Python) | `code_parser.py` |
| "Semantic search over code" as a stated capability | Realized here via the vector store, section B/C |

## B. Modified / re-scoped for this academic project

| CodeRAG capability | How it was re-scoped here | Why |
|---|---|---|
| Remote repo analysis via API (no cloning) | Local shallow `git clone` | Simpler, fully offline-capable, no per-provider auth needed for a demo |
| Tree-sitter/ts-morph based AST parsing for JS/TS/Java | Regex-based heuristic parsing (Python still uses real `ast`) | No native binary/tree-sitter grammar dependencies to install for grading |
| MCP tool interface (used by AI coding agents) | REST API + web UI (used by a human end user) | The brief's actual deliverable is an interactive natural-language Q&A product, not an agent-tool server |
| CK quality metrics / technical-debt scoring | Deliberately **not** implemented | Explicitly out of scope per the brief (section 4) |

## C. Newly implemented CodeInsight AI functionality (the project's contribution)

1. Code **chunking** for embedding (`services/chunker.py`)
2. **Vector store** integration — ChromaDB (`services/vector_store.py`)
3. **Hybrid retrieval** combining vector similarity with graph traversal
   (`services/hybrid_retrieval.py`)
4. **RAG pipeline**: prompt construction + LLM call for natural-language
   answers (`services/rag_pipeline.py`, `services/llm_service.py`)
5. **Explainable answers** with retrieved-source traceability
   (file/entity/line numbers, tagged vector vs. graph origin)
6. **AI Response Verification module**: Faithfulness, Answer Relevancy,
   Response Time (`services/verification.py`)
7. **User feedback** capture (👍/👎) and storage (`db/sqlite_store.py`,
   `routers/feedback.py`)
8. **Evaluation dashboard** and a reproducible evaluation script over a
   curated repository/question dataset (`evaluation/`)
9. Web **frontend** (Dashboard, Q&A, Evaluation) built specifically for
   CodeInsight AI (`frontend/`)

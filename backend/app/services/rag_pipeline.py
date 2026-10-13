"""
CodeInsight AI - RAG Pipeline Orchestrator
NEW (CodeInsight AI): wires together hybrid retrieval, prompt construction,
LLM generation and the verification module into the single Q&A pipeline
described in section 13 of the brief.
"""
import uuid
from . import hybrid_retrieval, llm_service, verification
from ..db import sqlite_store


def answer_question(repo_id: str, question: str):
    with verification.Timer() as t:
        retrieval = hybrid_retrieval.hybrid_retrieve(repo_id, question)
        context, sources = hybrid_retrieval.build_context_and_sources(retrieval)

        if not context.strip():
            answer_text = ("The repository context does not provide enough information "
                            "to answer this question. Try rephrasing, or confirm the "
                            "repository has finished indexing.")
        else:
            try:
                answer_text = llm_service.generate_answer(question, context)
            except llm_service.LLMError as e:
                answer_text = f"LLM generation failed: {e}"

        context_chunks = [h["text"] for h in retrieval["vector_hits"]] or [context]
        faithfulness, relevancy, f_method, r_method = verification.compute_faithfulness_and_relevancy(
            question, answer_text, context_chunks
        )

    response_time = round(t.elapsed, 3)
    answer_id = uuid.uuid4().hex[:16]

    sqlite_store.save_answer(
        answer_id=answer_id, repo_id=repo_id, question=question, answer=answer_text,
        sources=sources, faithfulness=faithfulness, relevancy=relevancy, response_time=response_time
    )

    return {
        "answer_id": answer_id,
        "question": question,
        "answer": answer_text,
        "sources": sources,
        "verification": {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "response_time_seconds": response_time,
            "faithfulness_method": f_method,
            "relevancy_method": r_method,
        },
    }

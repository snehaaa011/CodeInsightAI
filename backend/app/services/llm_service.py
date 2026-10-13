"""
CodeInsight AI - LLM Service

Thin abstraction over the LLM used for answer generation.
Supported providers:
    - anthropic
    - openai
    - gemini
    - mock

The RAG pipeline remains provider-independent.
"""

from ..config import settings


SYSTEM_PROMPT = (
    "You are CodeInsight AI, an assistant that explains software repositories. "
    "Answer the user's question ONLY using the provided repository context "
    "(retrieved code chunks and structural relationships). "
    "Cite file names you rely on. If the retrieved context does not contain "
    "enough information to answer confidently, say so explicitly rather than "
    "guessing or inventing details."
)


class LLMError(Exception):
    pass


def _build_user_prompt(question: str, context: str) -> str:
    return (
        "Repository context (retrieved code and structural relationships):\n"
        "---------------------------------------------\n"
        f"{context}\n"
        "---------------------------------------------\n\n"
        f"Question: {question}\n\n"
        "Answer clearly and concisely, referencing the relevant file(s)."
    )


def generate_answer(question: str, context: str) -> str:
    provider = settings.llm_provider.strip().lower()

    # ---------------------------------------------------------
    # Anthropic
    # ---------------------------------------------------------
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured.")

        try:
            import anthropic

            client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key
            )

            resp = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.llm_max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": _build_user_prompt(
                            question,
                            context
                        ),
                    }
                ],
            )

            return "".join(
                block.text
                for block in resp.content
                if hasattr(block, "text")
            ).strip()

        except Exception as exc:
            raise LLMError(
                f"Anthropic request failed: {exc}"
            ) from exc

    # ---------------------------------------------------------
    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key
            )

            resp = client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=settings.llm_max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": _build_user_prompt(
                            question,
                            context
                        ),
                    },
                ],
            )

            content = resp.choices[0].message.content

            if not content:
                raise LLMError(
                    "OpenAI returned an empty response."
                )

            return content.strip()

        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(
                f"OpenAI request failed: {exc}"
            ) from exc
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is not configured.")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=settings.gemini_api_key
            )

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=_build_user_prompt(
                    question,
                    context
                ),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=settings.llm_max_tokens,
                    temperature=0.2,
                ),
            )

            if not response.text:
                raise LLMError(
                    "Gemini returned an empty response."
                )

            return response.text.strip()

        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(
                f"Gemini request failed: {exc}"
            ) from exc
    if not context.strip():
        return (
            "The repository context does not provide enough information "
            "to answer this question."
        )

    snippet = context.strip().splitlines()
    preview = "\n".join(snippet[:12])

    return (
        f"[Mock LLM - no LLM_PROVIDER configured] "
        f"Based on the retrieved repository context, here is the most "
        f"relevant information for: \"{question}\"\n\n"
        f"{preview}\n\n"
        f"(Configure LLM_PROVIDER=anthropic, openai, or gemini "
        f"in .env for a real generated answer.)"
    )

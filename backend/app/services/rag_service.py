from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from typing import Optional

from app.config import settings
from app.services.retriever_service import get_retriever


SYSTEM_PROMPT = """You are GreenLens LM, an expert assistant on Indonesia's green economy,
environmental regulations, and energy transition policies.

Your knowledge base contains official documents:
- NDC 2022 — Indonesia's climate commitments (31.89% unconditional, 43.20% conditional)
- JETP CIPP 2023 + Progress Report 2025 — energy transition investment plan
- Perpres 98/2021 & 110/2025 — carbon pricing regulations
- KLHK regulations — AMDAL, environmental law (PP 22/2021, PermenLHK 4/2021, 21/2022)
- ESDM regulations — renewable energy (Perpres 112/2022, Permen ESDM 2/2024)
- OJK TKBI v3 2026 — sustainable finance taxonomy
- POJK 14/2023 — carbon exchange regulation

RULES:
1. Answer ONLY based on the provided context documents.
2. Always cite the regulation name and year (e.g. "According to Perpres 98/2021...").
3. If context is insufficient, say: "I couldn't find specific information about this in the available documents."
4. {language_instruction}
5. Use bullet points for lists of requirements or steps.
6. Even though the source documents may be in a different language than requested,
   ALWAYS translate your entire answer — including quoted terms, headers, and bullet
   labels — into the requested response language. Do not mix languages in your answer.

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Answer (fully in the requested response language):"""

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond ENTIRELY in English, regardless of what language the source documents or context are written in. Translate any Indonesian terms, regulation excerpts, or quotes into English.",
    "id": "Jawab SEPENUHNYA dalam Bahasa Indonesia, terlepas dari bahasa dokumen sumber atau konteks. Terjemahkan istilah, kutipan, atau cuplikan regulasi berbahasa Inggris ke dalam Bahasa Indonesia.",
}


def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def format_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return "No previous conversation."
    lines = []
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        default_headers={
            "HTTP-Referer": "https://greenlens-lm.onrender.com",
            "X-Title": "GreenLens LM",
        },
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_rag_response(
    question: str,
    language: str = "en",
    category_filter: Optional[str] = None,
    chat_history: list[dict] = [],
) -> dict:
    retriever = get_retriever(category_filter)
    llm = get_llm()

    language_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])

    prompt = PromptTemplate(
        input_variables=["context", "chat_history", "question", "language_instruction"],
        template=SYSTEM_PROMPT,
    )

    # Build LCEL chain — language_instruction is injected as a fixed value
    # for this request (not from user input), forcing the LLM's output
    # language regardless of what language the retrieved documents are in.
    chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "chat_history": RunnableLambda(lambda _: format_history(chat_history)),
            "question": RunnablePassthrough(),
            "language_instruction": RunnableLambda(lambda _: language_instruction),
        }
        | prompt
        | llm
    )

    # Retrieve docs separately for source citation
    source_docs = retriever.invoke(question)
    ai_message = await chain.ainvoke(question)

    answer = ai_message.content

    actual_model = (
        ai_message.response_metadata.get("model_name")
        or ai_message.response_metadata.get("model")
        or settings.LLM_MODEL
    )

    # Deduplicate sources
    sources = []
    seen = set()
    for doc in source_docs:
        meta = doc.metadata
        key = f"{meta.get('source_file', '')}:{meta.get('page', 0)}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "content": doc.page_content[:500].strip(),
                "source_file": meta.get("source_file", "unknown"),
                "regulation": meta.get("regulation", "unknown"),
                "category": meta.get("category", "unknown"),
                "year": int(meta.get("year", 0)),
                "page": int(meta.get("page", 0)),
            })

    logger.info(f"RAG complete — lang={language} — {len(sources)} sources — model: {actual_model}")
    return {"answer": answer, "sources": sources[:3], "model_used": actual_model}
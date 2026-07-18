import chromadb
from langchain_chroma import Chroma
from functools import lru_cache
from loguru import logger
from typing import Optional
from app.config import settings
from app.services.embed_service import get_embeddings


@lru_cache(maxsize=1)
def get_vectorstore() -> Chroma:
    """
    Connect to ChromaDB — cached across requests.
    Uses get_or_create_collection for ChromaDB 1.x compatibility.
    """
    logger.info(f"Connecting to ChromaDB: {settings.CHROMA_PATH}")

    # ChromaDB 1.x requires explicit client with get_or_create_collection
    # to avoid NotFoundError when the collection is first accessed
    client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    client.get_or_create_collection(name="greenlens_docs")

    return Chroma(
        client=client,
        embedding_function=get_embeddings(),
        collection_name="greenlens_docs",
    )


def get_retriever(category_filter: Optional[str] = None):
    """Build retriever with optional category metadata filter."""
    vectorstore = get_vectorstore()
    search_kwargs: dict = {"k": settings.RETRIEVER_K}
    if category_filter:
        search_kwargs["filter"] = {"category": category_filter}
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )

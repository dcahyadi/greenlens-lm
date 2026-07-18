from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from app.models.schemas import QueryRequest, QueryResponse
from app.services.rag_service import get_rag_response
from app.rate_limiter import rate_limit_dependency

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(rate_limit_dependency)])
async def query_documents(request: QueryRequest):
    """Query the GreenLens RAG pipeline. Returns AI answer with cited sources."""
    try:
        logger.info(f"Query: '{request.question[:80]}' | lang={request.language} | cat={request.category}")
        result = await get_rag_response(
            question=request.question,
            language=request.language,
            category_filter=request.category,
            chat_history=[m.model_dump() for m in request.chat_history],
        )
        return result
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process query. Please try again.")

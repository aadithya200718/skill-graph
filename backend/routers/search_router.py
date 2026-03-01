import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search")
async def search_concepts(q: str, top_k: int = 10, gaps: str = ""):
    from main import get_hybrid_rag
    rag = get_hybrid_rag()
    if not rag:
        return {"results": [], "error": "RAG service not initialized"}

    gap_ids = [g.strip() for g in gaps.split(",") if g.strip()] if gaps else None
    results = await rag.search(query=q, gap_ids=gap_ids, top_k=top_k)
    return {"query": q, "results": results, "count": len(results)}

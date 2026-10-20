"""Search endpoints: simple keyword search plus AWMF chunk search/RAG."""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import (
 ChunkResultItem,
 ChunkSearchResponse,
 RagResponse,
 RagSourceItem,
 SearchFilterOptions,
 SearchResponse,
 SearchResultItem,
)
from search.keyword import filter_options, search_keyword
from search.chunks import (
    EmbeddingError as ChunkEmbeddingError,
    LlamaserverConnectionError as ChunkLlamaserverError,
    search_chunks,
)
from search.rag import RagError, RagLlamaserverError, answer_rag

router = APIRouter(prefix="/search", tags=["search"])


def _to_result_item(item: dict) -> SearchResultItem:
    """Convert a keyword-search row to the API response format."""
    return SearchResultItem(
        id=item["id"],
        titel=item["titel"],
        zusammenfassung=item["zusammenfassung"],
        inhalt=item["inhalt"],
        dokumenttyp=item["dokumenttyp"],
        schwierigkeit=item["schwierigkeit"],
        unterkategorie=item["unterkategorie"],
        source_path=item["source_path"],
        created_at=str(item["created_at"]) if item["created_at"] else None,
        updated_at=str(item["updated_at"]) if item["updated_at"] else None,
        rank=item["rank"],
    )


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query("", description="Search query string (optional when filters are set)"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    fachgebiet: str | None = Query(None, description="Fachgebiet id or name"),
    dokumenttyp: str | None = Query(None, description="Dokumenttyp id or name"),
    folder: str | None = Query(None, description="Top-level source folder segment"),
    diagnose: str | None = Query(None, description="Diagnose id or name"),
    symptom: str | None = Query(None, description="Symptom id or name"),
    ordner_label: str | None = Query(None, description="Ordner-Label id or name"),
    db: Session = Depends(get_db),
):
    """Keyword search over entries: ILIKE substring matching with tier ranking.

    Optional filters (fachgebiet, dokumenttyp, folder) are ANDed on top of the
    keyword match. With only filters set (empty q), lists all matching entries.
    """
    try:
        items, total = search_keyword(
            db=db,
            query=q,
            limit=limit,
            offset=offset,
            fachgebiet=fachgebiet,
            dokumenttyp=dokumenttyp,
            folder=folder,
            diagnose=diagnose,
            symptom=symptom,
            ordner_label=ordner_label,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    return SearchResponse(
        items=[_to_result_item(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        query=q,
        filters=SearchFilterOptions(**filter_options(db)),
    )


@router.get("/chunks", response_model=ChunkSearchResponse)
async def search_chunks_endpoint(
    q: str = Query(..., min_length=1, description="Search query string (German)"),
    limit: int = Query(20, ge=1, le=50, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """Search AWMF chunks by vector similarity (Qwen3-Embedding via CPU sidecar)."""
    try:
        result = search_chunks(q, db, limit=limit, offset=offset)
    except ChunkLlamaserverError as e:
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {e}")
    except ChunkEmbeddingError as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")

    return ChunkSearchResponse(
        items=[ChunkResultItem(**item) for item in result["items"]],
        total=result["total"],
        limit=limit,
        offset=offset,
        query=q,
    )


@router.get("/chunks/rag", response_model=RagResponse)
async def rag_chunks_endpoint(
    q: str = Query(..., min_length=1, description="Question to answer (German)"),
    top_k: int = Query(6, ge=1, le=10, description="Number of passages fed to the model"),
    db: Session = Depends(get_db),
):
    """Answer a question over AWMF chunks: retrieve top-k, prompt the 9B, return answer + sources."""
    try:
        result = answer_rag(q, db, top_k=top_k)
    except RagLlamaserverError as e:
        raise HTTPException(status_code=503, detail=f"Chat service unavailable: {e}")
    except RagError as e:
        raise HTTPException(status_code=500, detail=f"RAG generation failed: {e}")

    return RagResponse(
        answer=result["answer"],
        sources=[RagSourceItem(**s) for s in result["sources"]],
        query=result["query"],
        model=result["model"],
    )

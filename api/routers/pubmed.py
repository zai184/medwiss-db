"""PubMed E-utilities proxy — live literature search with abstracts."""

from defusedxml.ElementTree import ParseError, fromstring
from datetime import date, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/pubmed", tags=["pubmed"])

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "medwiss-db"
EMAIL = "medwiss@example.com"  # NCBI requires a contact email for E-utilities

# PubMed Publication Type values (exact phrasing required by PubMed)
PUBMED_PTYPES: dict[str, str] = {
    "case_reports": "Case Reports",
    "clinical_study": "Clinical Study",
    "clinical_trial": "Clinical Trial",
    "dataset": "Dataset",
    "review": "Review",
}


class PubmedResult(BaseModel):
    pmid: str
    title: str
    authors: list[str]
    journal: str
    date: str
    doi: Optional[str] = None
    url: str
    abstract: Optional[str] = None


class PubmedSearchResponse(BaseModel):
    total: int
    results: list[PubmedResult]
    query: str


def _build_term(
    q: str = "",
    title: str = "",
    author: str = "",
    ptype: Optional[str] = None,
    publisher: str = "",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Build a PubMed Entrez query from structured filters."""
    clauses: list[str] = []
    if q.strip():
        clauses.append(f"({q.strip()})")
    if title.strip():
        clauses.append(f"({title.strip()}[Title])")
    if author.strip():
        clauses.append(f"({author.strip()}[Author])")
    if ptype:
        clauses.append(f"({PUBMED_PTYPES[ptype]}[Publication Type])")
    if publisher.strip():
        clauses.append(f"({publisher.strip()}[Journal])")
    if date_from and date_to:
        clauses.append(f"({date_from}:{date_to}[dp])")
    return " AND ".join(clauses)


async def _esearch(term: str, retmax: int, retstart: int, sort: str = "relevance") -> tuple[int, list[str]]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{EUTILS}/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": term,
                "retmode": "json",
                "retmax": retmax,
                "retstart": retstart,
                "sort": sort,
                "tool": TOOL,
                "email": EMAIL,
            },
        )
    resp.raise_for_status()
    data = resp.json()
    result = data.get("esearchresult", {})
    count = int(result.get("count", 0))
    idlist = result.get("idlist", [])
    return count, idlist


async def _esummary(pmids: list[str]) -> dict[str, dict[str, object]]:
    if not pmids:
        return {}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{EUTILS}/esummary.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
                "tool": TOOL,
                "email": EMAIL,
            },
        )
    resp.raise_for_status()
    data = resp.json().get("result", {})
    return {uid: data[uid] for uid in data.get("uids", [])}


async def _efetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Fetch abstracts via EFetch XML, keyed by PMID."""
    if not pmids:
        return {}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{EUTILS}/efetch.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "abstract",
                "retmode": "xml",
                "tool": TOOL,
                "email": EMAIL,
            },
        )
    resp.raise_for_status()

    abstracts: dict[str, str] = {}
    try:
        root = fromstring(resp.content)
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            if pmid_el is None:
                continue
            pmid = (pmid_el.text or "").strip()
            # Collect abstract text, preserving section labels (BACKGROUND, METHODS, ...)
            parts: list[str] = []
            for text_el in article.findall(".//Abstract/AbstractText"):
                label = text_el.get("Label")
                txt = "".join(text_el.itertext()).strip()
                if not txt:
                    continue
                parts.append(f"{label}: {txt}" if label else txt)
            if parts:
                abstracts[pmid] = " ".join(parts)
    except ParseError:
        pass  # abstract parsing failure should not fail the whole search
    return abstracts


@router.get("/search", response_model=PubmedSearchResponse)
async def search_pubmed(
    q: str = Query("", description="Free-text search term"),
    title: str = Query("", description="Restrict to title field"),
    author: str = Query("", description="Restrict to author field"),
    ptype: Optional[str] = Query(None, description="Publication type (case_reports, clinical_study, clinical_trial, dataset, review)"),
    publisher: str = Query("", description="Restrict to journal/publisher"),
    date_preset: Optional[str] = Query(None, description="Date preset: 1y, 5y, 10y, custom"),
    date_from: Optional[str] = Query(None, description="Custom range start (YYYY/MM/DD)"),
    date_to: Optional[str] = Query(None, description="Custom range end (YYYY/MM/DD)"),
    sort: str = Query("relevance", pattern="^(relevance|pub_date|Author|JournalName)$"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """Search PubMed with field filters, return metadata + inline abstract per result."""
    if not any([q, title, author, ptype, publisher, date_preset]):
        raise HTTPException(status_code=422, detail="At least one search field is required")

    # Resolve date range
    if date_preset == "custom":
        if not (date_from and date_to):
            raise HTTPException(status_code=422, detail="Custom date range requires date_from and date_to")
    elif date_preset:
        years = {"1y": 1, "5y": 5, "10y": 10}.get(date_preset)
        if years is None:
            raise HTTPException(status_code=422, detail=f"Invalid date_preset: {date_preset}")
        today = date.today()
        date_to = today.strftime("%Y/%m/%d")
        date_from = (today - timedelta(days=365 * years)).strftime("%Y/%m/%d")

    if ptype and ptype not in PUBMED_PTYPES:
        raise HTTPException(status_code=422, detail=f"Invalid ptype: {ptype}")

    term = _build_term(q=q, title=title, author=author, ptype=ptype, publisher=publisher, date_from=date_from, date_to=date_to)

    try:
        total, idlist = await _esearch(term, retmax=limit, retstart=offset, sort=sort)
        summaries = await _esummary(idlist)
        abstracts = await _efetch_abstracts(idlist)

        results: list[PubmedResult] = []
        for pmid in idlist:
            s = summaries.get(pmid, {})
            doi = None
            eloc = s.get("elocationid") or ""
            if "doi:" in eloc:
                doi = eloc.split("doi:", 1)[1].strip()
            authors = [a.get("name", "") for a in s.get("authors", []) if a.get("name")]
            results.append(
                PubmedResult(
                    pmid=pmid,
                    title=s.get("title") or "Untitled",
                    authors=authors,
                    journal=s.get("fulljournalname") or "",
                    date=s.get("pubdate") or "",
                    doi=doi,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    abstract=abstracts.get(pmid),
                )
            )
        return PubmedSearchResponse(total=total, results=results, query=term)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"PubMed request failed: {e}")

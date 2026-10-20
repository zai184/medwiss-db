"""API router for dashboard statistics."""

from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from database.models import (
    Diagnose,
    Dokumenttyp,
    Fachgebiet,
    KnowledgeEntry,
)

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class StatsOverview(BaseModel):
    """Overview statistics for the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    total_entries: int
    entries_by_category: Dict[str, int]


class CategoryStats(BaseModel):
    """Statistics per category."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    count: int
    percentage: float


class FachStats(BaseModel):
    """Statistics per Fachgebiet."""

    model_config = ConfigDict(from_attributes=True)

    fachgebiet_id: int
    fachgebiet_name: str
    count: int


class DiagnoseStats(BaseModel):
    """Statistics per Diagnose."""

    model_config = ConfigDict(from_attributes=True)

    diagnose_id: int
    diagnose_name: str
    diagnose_code: str
    count: int


class RecentEntry(BaseModel):
    """Recent entry for activity list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titel: str
    zusammenfassung: str | None
    dokumenttyp: str | None
    created_at: str
    fachgebiete: List[dict]


# =============================================================================
# Stats Endpoints
# =============================================================================


@router.get("/overview", response_model=StatsOverview)
def get_stats_overview(
    db: Session = Depends(get_db),
) -> StatsOverview:
    """Get overview statistics for the dashboard."""
    # Total entries
    total_entries = db.query(KnowledgeEntry).count()

    # Entries by dokumenttyp
    category_counts = (
        db.query(KnowledgeEntry.dokumenttyp, func.count(KnowledgeEntry.id))
        .group_by(KnowledgeEntry.dokumenttyp)
        .all()
    )
    entries_by_category = {str(cat or "Unkategorisiert"): count for cat, count in category_counts}

    return StatsOverview(
        total_entries=total_entries,
        entries_by_category=entries_by_category,
    )


@router.get("/by-category", response_model=List[CategoryStats])
def get_stats_by_category(
    db: Session = Depends(get_db),
) -> List[CategoryStats]:
    """Get statistics grouped by dokumenttyp."""
    total = db.query(KnowledgeEntry).count()

    if total == 0:
        return []

    results = (
        db.query(
            func.coalesce(Dokumenttyp.name, KnowledgeEntry.dokumenttyp).label("category"),
            func.count(KnowledgeEntry.id),
        )
        .outerjoin(Dokumenttyp, KnowledgeEntry.dokumenttyp_id == Dokumenttyp.id)
        .group_by(func.coalesce(Dokumenttyp.name, KnowledgeEntry.dokumenttyp))
        .order_by(func.count(KnowledgeEntry.id).desc())
        .all()
    )

    return [
        CategoryStats(
            category=str(cat or "Unkategorisiert"),
            count=count,
            percentage=round((count / total) * 100, 1),
        )
        for cat, count in results
    ]


@router.get("/by-fach", response_model=List[FachStats])
def get_stats_by_fach(
    db: Session = Depends(get_db),
) -> List[FachStats]:
    """Get statistics grouped by Fachgebiet."""
    from database.models import entry_fach_table as entry_fach

    results = (
        db.query(Fachgebiet.id, Fachgebiet.name, func.count(entry_fach.c.entry_id))
        .join(entry_fach, Fachgebiet.id == entry_fach.c.fach_id)
        .group_by(Fachgebiet.id, Fachgebiet.name)
        .order_by(func.count(entry_fach.c.entry_id).desc())
        .all()
    )

    return [
        FachStats(fachgebiet_id=fach_id, fachgebiet_name=fach_name, count=count)
        for fach_id, fach_name, count in results
    ]


@router.get("/by-diagnose", response_model=List[DiagnoseStats])
def get_stats_by_diagnose(
    db: Session = Depends(get_db),
    limit: int = 10,
) -> List[DiagnoseStats]:
    """Get statistics grouped by Diagnose."""
    from database.models import entry_diagnose_table as entry_diagnose

    results = (
        db.query(Diagnose.id, Diagnose.name, Diagnose.code, func.count(entry_diagnose.c.entry_id))
        .join(entry_diagnose, Diagnose.id == entry_diagnose.c.diagnose_id)
        .group_by(Diagnose.id, Diagnose.name, Diagnose.code)
        .order_by(func.count(entry_diagnose.c.entry_id).desc())
        .limit(limit)
        .all()
    )

    return [
        DiagnoseStats(
            diagnose_id=diag_id, diagnose_name=diag_name, diagnose_code=diag_code, count=count
        )
        for diag_id, diag_name, diag_code, count in results
    ]


@router.get("/recent", response_model=List[RecentEntry])
def get_recent_entries(
    db: Session = Depends(get_db),
    limit: int = 5,
) -> List[RecentEntry]:
    """Get the most recent entries for the activity list."""
    entries = db.query(KnowledgeEntry).order_by(KnowledgeEntry.created_at.desc()).limit(limit).all()

    return [
        RecentEntry(
            id=entry.id,
            titel=entry.titel,
            zusammenfassung=entry.zusammenfassung,
            dokumenttyp=entry.dokumenttyp,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            fachgebiete=[{"id": f.id, "name": f.name} for f in entry.fachgebiete],
        )
        for entry in entries
    ]

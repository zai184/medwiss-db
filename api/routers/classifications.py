"""API router for classifications (Fachgebiete, Diagnosen, Symptome)."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from api.models import (
    DokumenttypCreate,
    DokumenttypResponse,
    DokumenttypUpdate,
    OrdnerLabelCreate,
    OrdnerLabelResponse,
    OrdnerLabelUpdate,
    ResolveLabelsRequest,
    ResolveLabelsResponse,
)
from api.services.tagging_service import TaggingService
from api.database import get_db
from database.models import (
    Diagnose,
    Dokumenttyp,
    Fachgebiet,
    KnowledgeEntry,
    OrdnerLabel,
    Symptom,
)

router = APIRouter(
    prefix="",
    tags=["classifications"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class FachgebietBase(BaseModel):
    """Base schema for Fachgebiet."""

    name: str
    beschreibung: Optional[str] = None


class FachgebietCreate(FachgebietBase):
    """Schema for creating a Fachgebiet."""

    pass


class FachgebietUpdate(BaseModel):
    """Schema for updating a Fachgebiet."""

    name: Optional[str] = None
    beschreibung: Optional[str] = None


class FachgebietResponse(FachgebietBase):
    """Response schema for Fachgebiet."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None


class DiagnoseBase(BaseModel):
    """Base schema for Diagnose."""

    code: str
    name: str
    beschreibung: Optional[str] = None


class DiagnoseCreate(DiagnoseBase):
    """Schema for creating a Diagnose."""

    pass


class DiagnoseUpdate(BaseModel):
    """Schema for updating a Diagnose."""

    code: Optional[str] = None
    name: Optional[str] = None
    beschreibung: Optional[str] = None


class DiagnoseResponse(DiagnoseBase):
    """Response schema for Diagnose."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None


class SymptomBase(BaseModel):
    """Base schema for Symptom."""

    name: str
    beschreibung: Optional[str] = None


class SymptomCreate(SymptomBase):
    """Schema for creating a Symptom."""

    pass


class SymptomUpdate(BaseModel):
    """Schema for updating a Symptom."""

    name: Optional[str] = None
    beschreibung: Optional[str] = None


class SymptomResponse(SymptomBase):
    """Response schema for Symptom."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None


class KnowledgeEntrySummary(BaseModel):
    """Summary schema for KnowledgeEntry (used in list responses)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titel: str
    zusammenfassung: Optional[str] = None,
    status: str
    dokumenttyp: Optional[str] = None
    schwierigkeit: Optional[str] = None
    created_at: Optional[str] = None


# =============================================================================
# Fachgebiete Endpoints
# =============================================================================


@router.get("/fachgebiete", response_model=List[FachgebietResponse])
def get_all_fachgebiete(
    skip: int = 0,
    limit: int = 10000,
    reviewed_only: bool = False,
    db: Session = Depends(get_db),
) -> List[Fachgebiet]:
    """Get all Fachgebiete (medical specialties)."""
    query = db.query(Fachgebiet)
    if reviewed_only:
        query = query.filter(Fachgebiet.needs_review.is_(False))
    fachgebiete = query.offset(skip).limit(limit).all()
    return fachgebiete


@router.get("/fachgebiete/{fach_id}", response_model=FachgebietResponse)
def get_fachgebiet(
    fach_id: int,
    db: Session = Depends(get_db),
) -> Fachgebiet:
    """Get a single Fachgebiet by ID."""
    fachgebiet = db.query(Fachgebiet).filter(Fachgebiet.id == fach_id).first()
    if not fachgebiet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fachgebiet with ID {fach_id} not found",
        )
    return fachgebiet


@router.get("/fachgebiete/{fach_id}/entries", response_model=List[KnowledgeEntrySummary])
def get_entries_by_fachgebiet(
    fach_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[KnowledgeEntry]:
    """Get all knowledge entries associated with a specific Fachgebiet."""
    # Check if fachgebiet exists
    fachgebiet = db.query(Fachgebiet).filter(Fachgebiet.id == fach_id).first()
    if not fachgebiet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fachgebiet with ID {fach_id} not found",
        )

    # Get entries via M2M relationship
    entries = (
        db.query(KnowledgeEntry)
        .join(Fachgebiet.entries)
        .filter(Fachgebiet.id == fach_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries


@router.post(
    "/fachgebiete",
    response_model=FachgebietResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_fachgebiet(
    fachgebiet: FachgebietCreate,
    db: Session = Depends(get_db),
) -> Fachgebiet:
    """Create a new Fachgebiet (Admin only)."""
    # Check for duplicate name
    existing = db.query(Fachgebiet).filter(Fachgebiet.name == fachgebiet.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fachgebiet with name '{fachgebiet.name}' already exists",
        )

    db_fachgebiet = Fachgebiet(
        name=fachgebiet.name,
        beschreibung=fachgebiet.beschreibung,
    )
    db.add(db_fachgebiet)
    db.commit()
    db.refresh(db_fachgebiet)
    return db_fachgebiet


@router.put("/fachgebiete/{fach_id}", response_model=FachgebietResponse)
def update_fachgebiet(
    fach_id: int,
    fachgebiet_update: FachgebietUpdate,
    db: Session = Depends(get_db),
) -> Fachgebiet:
    """Update a Fachgebiet (Admin only)."""
    db_fachgebiet = db.query(Fachgebiet).filter(Fachgebiet.id == fach_id).first()
    if not db_fachgebiet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fachgebiet with ID {fach_id} not found",
        )

    # Check for name conflict if updating name
    if fachgebiet_update.name and fachgebiet_update.name != db_fachgebiet.name:
        existing = db.query(Fachgebiet).filter(Fachgebiet.name == fachgebiet_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Fachgebiet with name '{fachgebiet_update.name}' already exists",
            )
        db_fachgebiet.name = fachgebiet_update.name

    if fachgebiet_update.beschreibung is not None:
        db_fachgebiet.beschreibung = fachgebiet_update.beschreibung

    db.commit()
    db.refresh(db_fachgebiet)
    return db_fachgebiet


@router.delete("/fachgebiete/{fach_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fachgebiet(
    fach_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a Fachgebiet (Admin only)."""
    db_fachgebiet = db.query(Fachgebiet).filter(Fachgebiet.id == fach_id).first()
    if not db_fachgebiet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fachgebiet with ID {fach_id} not found",
        )

    db.delete(db_fachgebiet)
    db.commit()


# =============================================================================
# Diagnosen Endpoints
# =============================================================================


@router.get("/diagnosen", response_model=List[DiagnoseResponse])
def get_all_diagnosen(
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_db),
) -> List[Diagnose]:
    """Get all Diagnosen (diagnoses)."""
    diagnosen = db.query(Diagnose).offset(skip).limit(limit).all()
    return diagnosen


@router.get("/diagnosen/{diagnose_id}", response_model=DiagnoseResponse)
def get_diagnose(
    diagnose_id: int,
    db: Session = Depends(get_db),
) -> Diagnose:
    """Get a single Diagnose by ID."""
    diagnose = db.query(Diagnose).filter(Diagnose.id == diagnose_id).first()
    if not diagnose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnose with ID {diagnose_id} not found",
        )
    return diagnose


@router.get("/diagnosen/{diagnose_id}/entries", response_model=List[KnowledgeEntrySummary])
def get_entries_by_diagnose(
    diagnose_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[KnowledgeEntry]:
    """Get all knowledge entries associated with a specific Diagnose."""
    # Check if diagnose exists
    diagnose = db.query(Diagnose).filter(Diagnose.id == diagnose_id).first()
    if not diagnose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnose with ID {diagnose_id} not found",
        )

    # Get entries via M2M relationship
    entries = (
        db.query(KnowledgeEntry)
        .join(Diagnose.entries)
        .filter(Diagnose.id == diagnose_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries


@router.post(
    "/diagnosen",
    response_model=DiagnoseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_diagnose(
    diagnose: DiagnoseCreate,
    db: Session = Depends(get_db),
) -> Diagnose:
    """Create a new Diagnose (Admin only)."""
    # Check for duplicate code
    existing = db.query(Diagnose).filter(Diagnose.code == diagnose.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Diagnose with code '{diagnose.code}' already exists",
        )

    db_diagnose = Diagnose(
        code=diagnose.code,
        name=diagnose.name,
        beschreibung=diagnose.beschreibung,
    )
    db.add(db_diagnose)
    db.commit()
    db.refresh(db_diagnose)
    return db_diagnose


@router.put("/diagnosen/{diagnose_id}", response_model=DiagnoseResponse)
def update_diagnose(
    diagnose_id: int,
    diagnose_update: DiagnoseUpdate,
    db: Session = Depends(get_db),
) -> Diagnose:
    """Update a Diagnose (Admin only)."""
    db_diagnose = db.query(Diagnose).filter(Diagnose.id == diagnose_id).first()
    if not db_diagnose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnose with ID {diagnose_id} not found",
        )

    # Check for code conflict if updating code
    if diagnose_update.code and diagnose_update.code != db_diagnose.code:
        existing = db.query(Diagnose).filter(Diagnose.code == diagnose_update.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Diagnose with code '{diagnose_update.code}' already exists",
            )
        db_diagnose.code = diagnose_update.code

    if diagnose_update.name is not None:
        db_diagnose.name = diagnose_update.name

    if diagnose_update.beschreibung is not None:
        db_diagnose.beschreibung = diagnose_update.beschreibung

    db.commit()
    db.refresh(db_diagnose)
    return db_diagnose


@router.delete("/diagnosen/{diagnose_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diagnose(
    diagnose_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a Diagnose (Admin only)."""
    db_diagnose = db.query(Diagnose).filter(Diagnose.id == diagnose_id).first()
    if not db_diagnose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnose with ID {diagnose_id} not found",
        )

    db.delete(db_diagnose)
    db.commit()


# =============================================================================
# Symptome Endpoints
# =============================================================================


@router.get("/symptome", response_model=List[SymptomResponse])
def get_all_symptome(
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_db),
) -> List[Symptom]:
    """Get all Symptome (symptoms)."""
    symptome = db.query(Symptom).offset(skip).limit(limit).all()
    return symptome


@router.get("/symptome/{symptom_id}", response_model=SymptomResponse)
def get_symptom(
    symptom_id: int,
    db: Session = Depends(get_db),
) -> Symptom:
    """Get a single Symptom by ID."""
    symptom = db.query(Symptom).filter(Symptom.id == symptom_id).first()
    if not symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symptom with ID {symptom_id} not found",
        )
    return symptom


@router.get("/symptome/{symptom_id}/entries", response_model=List[KnowledgeEntrySummary])
def get_entries_by_symptom(
    symptom_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[KnowledgeEntry]:
    """Get all knowledge entries associated with a specific Symptom."""
    # Check if symptom exists
    symptom = db.query(Symptom).filter(Symptom.id == symptom_id).first()
    if not symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symptom with ID {symptom_id} not found",
        )

    # Get entries via M2M relationship
    entries = (
        db.query(KnowledgeEntry)
        .join(Symptom.entries)
        .filter(Symptom.id == symptom_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries


@router.post(
    "/symptome",
    response_model=SymptomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_symptom(
    symptom: SymptomCreate,
    db: Session = Depends(get_db),
) -> Symptom:
    """Create a new Symptom (Admin only)."""
    # Check for duplicate name
    existing = db.query(Symptom).filter(Symptom.name == symptom.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Symptom with name '{symptom.name}' already exists",
        )

    db_symptom = Symptom(
        name=symptom.name,
        beschreibung=symptom.beschreibung,
    )
    db.add(db_symptom)
    db.commit()
    db.refresh(db_symptom)
    return db_symptom


@router.put("/symptome/{symptom_id}", response_model=SymptomResponse)
def update_symptom(
    symptom_id: int,
    symptom_update: SymptomUpdate,
    db: Session = Depends(get_db),
) -> Symptom:
    """Update a Symptom (Admin only)."""
    db_symptom = db.query(Symptom).filter(Symptom.id == symptom_id).first()
    if not db_symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symptom with ID {symptom_id} not found",
        )

    # Check for name conflict if updating name
    if symptom_update.name and symptom_update.name != db_symptom.name:
        existing = db.query(Symptom).filter(Symptom.name == symptom_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Symptom with name '{symptom_update.name}' already exists",
            )
        db_symptom.name = symptom_update.name

    if symptom_update.beschreibung is not None:
        db_symptom.beschreibung = symptom_update.beschreibung

    db.commit()
    db.refresh(db_symptom)
    return db_symptom


@router.delete("/symptome/{symptom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_symptom(
    symptom_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a Symptom (Admin only)."""
    db_symptom = db.query(Symptom).filter(Symptom.id == symptom_id).first()
    if not db_symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symptom with ID {symptom_id} not found",
        )

    db.delete(db_symptom)
    db.commit()


# =============================================================================
# Dokumenttypen Endpoints
# =============================================================================


@router.get("/dokumenttypen", response_model=List[DokumenttypResponse])
def get_all_dokumenttypen(
    skip: int = 0,
    limit: int = 10000,
    reviewed_only: bool = False,
    db: Session = Depends(get_db),
) -> List[Dokumenttyp]:
    """Get all Dokumenttypen (document types)."""
    query = db.query(Dokumenttyp)
    if reviewed_only:
        query = query.filter(Dokumenttyp.needs_review.is_(False))
    return query.offset(skip).limit(limit).all()


@router.post(
    "/dokumenttypen",
    response_model=DokumenttypResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dokumenttyp(
    dokumenttyp: DokumenttypCreate,
    db: Session = Depends(get_db),
) -> Dokumenttyp:
    """Create a new Dokumenttyp (Admin only)."""
    existing = db.query(Dokumenttyp).filter(Dokumenttyp.name == dokumenttyp.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dokumenttyp with name '{dokumenttyp.name}' already exists",
        )

    db_dokumenttyp = Dokumenttyp(name=dokumenttyp.name)
    db.add(db_dokumenttyp)
    db.commit()
    db.refresh(db_dokumenttyp)
    return db_dokumenttyp


@router.put("/dokumenttypen/{dokumenttyp_id}", response_model=DokumenttypResponse)
def update_dokumenttyp(
    dokumenttyp_id: int,
    dokumenttyp_update: DokumenttypUpdate,
    db: Session = Depends(get_db),
) -> Dokumenttyp:
    """Rename a Dokumenttyp (Admin only)."""
    db_dokumenttyp = db.query(Dokumenttyp).filter(Dokumenttyp.id == dokumenttyp_id).first()
    if not db_dokumenttyp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dokumenttyp with ID {dokumenttyp_id} not found",
        )

    if dokumenttyp_update.name != db_dokumenttyp.name:
        existing = (
            db.query(Dokumenttyp).filter(Dokumenttyp.name == dokumenttyp_update.name).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dokumenttyp with name '{dokumenttyp_update.name}' already exists",
            )
        db_dokumenttyp.name = dokumenttyp_update.name

    db.commit()
    db.refresh(db_dokumenttyp)
    return db_dokumenttyp


@router.delete("/dokumenttypen/{dokumenttyp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dokumenttyp(
    dokumenttyp_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a Dokumenttyp (Admin only). Entries keep their legacy string (FK SET NULL)."""
    db_dokumenttyp = db.query(Dokumenttyp).filter(Dokumenttyp.id == dokumenttyp_id).first()
    if not db_dokumenttyp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dokumenttyp with ID {dokumenttyp_id} not found",
        )

    db.delete(db_dokumenttyp)
    db.commit()


# =============================================================================
# Ordner-Labels Endpoints
# =============================================================================


@router.get("/ordner-labels", response_model=List[OrdnerLabelResponse])
def get_all_ordner_labels(
    skip: int = 0,
    limit: int = 10000,
    reviewed_only: bool = False,
    db: Session = Depends(get_db),
) -> List[OrdnerLabel]:
    """Get all Ordner-Labels (folder labels)."""
    query = db.query(OrdnerLabel)
    if reviewed_only:
        query = query.filter(OrdnerLabel.needs_review.is_(False))
    return query.offset(skip).limit(limit).all()


@router.post(
    "/ordner-labels",
    response_model=OrdnerLabelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ordner_label(
    ordner_label: OrdnerLabelCreate,
    db: Session = Depends(get_db),
) -> OrdnerLabel:
    """Create a new Ordner-Label (Admin only)."""
    existing = db.query(OrdnerLabel).filter(OrdnerLabel.name == ordner_label.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ordner-Label with name '{ordner_label.name}' already exists",
        )

    db_ordner_label = OrdnerLabel(name=ordner_label.name)
    db.add(db_ordner_label)
    db.commit()
    db.refresh(db_ordner_label)
    return db_ordner_label


@router.put("/ordner-labels/{ordner_label_id}", response_model=OrdnerLabelResponse)
def update_ordner_label(
    ordner_label_id: int,
    ordner_label_update: OrdnerLabelUpdate,
    db: Session = Depends(get_db),
) -> OrdnerLabel:
    """Rename an Ordner-Label (Admin only)."""
    db_ordner_label = (
        db.query(OrdnerLabel).filter(OrdnerLabel.id == ordner_label_id).first()
    )
    if not db_ordner_label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ordner-Label with ID {ordner_label_id} not found",
        )

    if ordner_label_update.name != db_ordner_label.name:
        existing = (
            db.query(OrdnerLabel).filter(OrdnerLabel.name == ordner_label_update.name).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ordner-Label with name '{ordner_label_update.name}' already exists",
            )
        db_ordner_label.name = ordner_label_update.name

    db.commit()
    db.refresh(db_ordner_label)
    return db_ordner_label


@router.delete("/ordner-labels/{ordner_label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ordner_label(
    ordner_label_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete an Ordner-Label (Admin only). Junction rows cascade."""
    db_ordner_label = (
        db.query(OrdnerLabel).filter(OrdnerLabel.id == ordner_label_id).first()
    )
    if not db_ordner_label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ordner-Label with ID {ordner_label_id} not found",
        )

    db.delete(db_ordner_label)
    db.commit()


# =============================================================================
# Tag resolution & review queue
# =============================================================================


class PendingReviewItem(BaseModel):
    """Classification lookup awaiting admin review."""

    kind: str
    id: int
    name: str
    code: Optional[str] = None
    source: str = "llm"
    beschreibung: Optional[str] = None


class PendingReviewResponse(BaseModel):
    """All classification lookups pending review."""

    items: list[PendingReviewItem]
    total: int


@router.post("/resolve-labels", response_model=ResolveLabelsResponse)
def resolve_labels(
    body: ResolveLabelsRequest,
    db: Session = Depends(get_db),
) -> ResolveLabelsResponse:
    """Resolve string labels to lookup IDs (creates missing rows)."""
    service = TaggingService(db)
    result = service.resolve_labels_to_ids(
        fachgebiete=body.fachgebiete,
        diagnosen=body.diagnosen,
        symptome=body.symptome,
        dokumenttyp=body.dokumenttyp,
        ordner_labels=body.ordner_labels,
    )
    return ResolveLabelsResponse(**result)


@router.get("/pending-review", response_model=PendingReviewResponse)
def get_pending_review(
    db: Session = Depends(get_db),
) -> PendingReviewResponse:
    """List classification lookups awaiting admin review."""
    items: list[PendingReviewItem] = []
    for kind, model in [
        ("fachgebiet", Fachgebiet),
        ("diagnose", Diagnose),
        ("symptom", Symptom),
        ("dokumenttyp", Dokumenttyp),
        ("ordner_label", OrdnerLabel),
    ]:
        rows = db.query(model).filter(model.needs_review.is_(True)).order_by(model.name).all()
        for row in rows:
            items.append(
                PendingReviewItem(
                    kind=kind,
                    id=row.id,
                    name=row.name,
                    code=getattr(row, "code", None),
                    source=getattr(row, "source", "llm"),
                    beschreibung=getattr(row, "beschreibung", None),
                )
            )
    return PendingReviewResponse(items=items, total=len(items))

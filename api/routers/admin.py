"""Admin API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.services.icd11 import ICD11Client
from api.services.regex_classifier import RegexClassifier


router = APIRouter(prefix="/admin", tags=["admin"])


class ClassifyFromFilenameRequest(BaseModel):
    force: bool = False
    dry_run: bool = True
    limit: Optional[int] = None


@router.post("/classify-from-filename")
async def classify_from_filename(
    body: ClassifyFromFilenameRequest,
    db: Session = Depends(get_db),
):
    """Classify entries deterministically by regex-matching folder + filename
    against the classification library (data/classification_library.txt).

    No LLM — instant and reproducible. Fachgebiet from folder, Diagnose and
    Symptom from filename. Then ICD-11 codes are enriched via the WHO API
    (optional — requires ICD11_CLIENT_ID/SECRET in .env).
    """
    icd11 = ICD11Client(
        client_id=settings.icd11_client_id,
        client_secret=settings.icd11_client_secret,
    )
    try:
        classifier = RegexClassifier(db, icd11=icd11)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Classification library missing on this deployment "
                "(data/classification_library.txt not deployed). "
                f"Details: {exc}"
            ),
        ) from exc
    result = await classifier.classify_all(
        force=body.force,
        dry_run=body.dry_run,
        limit=body.limit,
    )
    return result

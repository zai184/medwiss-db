import re
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from config import load_sources

router = APIRouter(
    prefix="/sources",
    tags=["sources"],
)


def _clean_display_name(name: str) -> str:
    return re.sub(r'^\d+_', '', name)


class SourceInfo(BaseModel):
    name: str
    display_name: str
    category: str
    description: str
    file_types: List[str]
    default_fachgebiete: List[str]
    subcategories: List[str]


@router.get("", response_model=List[SourceInfo])
def get_sources() -> List[SourceInfo]:
    sources = load_sources()
    return [
        SourceInfo(
            name=s.name,
            display_name=_clean_display_name(s.name),
            category=s.category,
            description=s.description,
            file_types=s.file_types,
            default_fachgebiete=s.default_fachgebiete,
            subcategories=s.subcategories,
        )
        for s in sources
    ]

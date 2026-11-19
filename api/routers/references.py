"""Referenz page — live-parsed medical resource links from medlinks.txt."""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import get_content_root

logger = logging.getLogger(__name__)

router = APIRouter(tags=["references"])

MEDLINKS_PATH = get_content_root() / "md" / "medlinks.txt"


URL_RE = re.compile(r"https?://\S+")
DOMAIN_RE = re.compile(r"^[\w.-]+\.\w{2,}$")


class Link(BaseModel):
    label: str
    url: str


class SubSection(BaseModel):
    title: str | None = None
    links: list[Link]


class Section(BaseModel):
    title: str
    sub: list[SubSection]


def _normalise_url(raw: str) -> str:
    """Ensure bare domains get https:// prefix."""
    raw = raw.strip().rstrip("*").strip()
    if DOMAIN_RE.match(raw):
        return f"https://{raw}"
    return raw


def _label_from_url(url: str) -> str:
    """Derive a human-readable label from a URL."""
    clean = url.removeprefix("https://").removeprefix("http://")
    clean = clean.removeprefix("www.")
    return clean.split("/")[0]


def parse_medlinks(path: Path = MEDLINKS_PATH) -> list[Section]:
    """Parse medlinks.txt into structured sections."""
    if not path.exists():
        raise FileNotFoundError(f"medlinks.txt not found at {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    sections: list[Section] = []
    current_section: Section | None = None
    current_sub: SubSection | None = None
    pending_label: str | None = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            pending_label = None
            continue

        # Section headers
        if stripped.startswith("### "):
            title = stripped[4:].strip()
            if current_section is None:
                current_section = Section(title="Sonstiges", sub=[])
                sections.append(current_section)
            current_sub = SubSection(title=title, links=[])
            current_section.sub.append(current_sub)
            pending_label = None
            continue

        if stripped.startswith("## "):
            title = stripped[3:].strip()
            if current_section is None:
                current_section = Section(title="Sonstiges", sub=[])
                sections.append(current_section)
            current_sub = SubSection(title=title, links=[])
            current_section.sub.append(current_sub)
            pending_label = None
            continue

        if stripped.startswith("# "):
            title = stripped[2:].strip()
            current_section = Section(title=title, sub=[])
            sections.append(current_section)
            current_sub = None
            pending_label = None
            continue

        # Labeled link: "* Label" → next indented line is URL
        if stripped.startswith("* "):
            pending_label = stripped[2:].strip()
            continue

        # URL line
        url_match = URL_RE.search(stripped)
        if url_match:
            url = _normalise_url(url_match.group(0))
            label = pending_label or _label_from_url(url)
            link = Link(label=label, url=url)
            if current_sub is not None:
                current_sub.links.append(link)
            elif current_section is not None:
                if not current_section.sub or current_section.sub[-1].title is not None:
                    current_section.sub.append(SubSection(title=None, links=[]))
                current_section.sub[-1].links.append(link)
            pending_label = None
            continue

        # Bare domain without protocol
        if DOMAIN_RE.match(stripped):
            url = f"https://{stripped}"
            label = pending_label or stripped
            link = Link(label=label, url=url)
            if current_sub is not None:
                current_sub.links.append(link)
            elif current_section is not None:
                if not current_section.sub or current_section.sub[-1].title is not None:
                    current_section.sub.append(SubSection(title=None, links=[]))
                current_section.sub[-1].links.append(link)
            pending_label = None
            continue

        pending_label = None

    return sections


@router.get("/references")
async def get_references() -> list[Section]:
    """Return medical resource links parsed live from medlinks.txt."""
    try:
        return parse_medlinks()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="medlinks.txt not found")


CALCULATORS_PATH = get_content_root() / "md" / "calculators.txt"


class Calculator(BaseModel):
    name: str
    url: str
    discipline: str
    group: str | None = None
    keywords: list[str] = []


def parse_calculators(path: Path = CALCULATORS_PATH) -> list[Calculator]:
    """Parse calculators.txt into curated calculator links.

    One calculator per line: Discipline | Group | Name | URL | kw, kw, …
    `Group` may be empty; `#` lines are comments; malformed lines are skipped
    with a warning (a typo must not silently drop a favorite).
    """
    calculators: list[Calculator] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        if len(parts) != 5 or not parts[0] or not parts[2] or not parts[3]:
            logger.warning("calculators.txt:%d: malformed line skipped: %r", lineno, stripped)
            continue
        calculators.append(
            Calculator(
                discipline=parts[0],
                group=parts[1] or None,
                name=parts[2],
                url=parts[3],
                keywords=[k.strip() for k in parts[4].split(",") if k.strip()],
            )
        )
    return calculators


@router.get("/calculators")
async def get_calculators() -> list[Calculator]:
    """Return curated calculator deep links parsed live from calculators.txt."""
    try:
        return parse_calculators()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="calculators.txt not found")

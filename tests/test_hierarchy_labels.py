"""Tests for folder-hierarchy label extraction."""

from pathlib import Path

import pytest

from unittest.mock import MagicMock

from api.services.hierarchy_labels import (
    CATEGORY_LABELS,
    MAX_HIERARCHY_DEPTH,
    extract_hierarchical_labels,
    extract_tag_suggestions_for_entry,
    humanize_folder_label,
)
from config import SourceConfig


@pytest.fixture
def leitlinien_source():
    return SourceConfig(
        name="2_Leitlinien",
        path="../2_Leitlinien",
        category="leitlinien",
    )


def test_humanize_strips_org_prefix():
    assert humanize_folder_label("DRG_Radiologie") == "Radiologie"
    assert humanize_folder_label("DEGAM_Leitlinien") == "Leitlinien"
    assert humanize_folder_label("DGOU_Orthopaedie_Unfallchirurgie") == "Orthopaedie Unfallchirurgie"
    assert humanize_folder_label("038-013_Demenzen") == "Demenzen"


def test_four_level_hierarchy(leitlinien_source):
    root = Path("/data/2_Leitlinien")
    file_path = root / "Primärversorgung" / "DEGAM_Leitlinien" / "Müdigkeit" / "doc.pdf"

    labels, unterkategorie = extract_hierarchical_labels(file_path, leitlinien_source, root)

    assert labels == ["Primärversorgung", "Leitlinien", "Müdigkeit"]
    assert unterkategorie == "Müdigkeit"


def test_root_level_file_uses_category_label(leitlinien_source):
    sop_source = SourceConfig(name="1_SOPs", path="../1_SOPs", category="sop")
    root = Path("/data/1_SOPs")
    file_path = root / "protocol.pdf"

    labels, unterkategorie = extract_hierarchical_labels(file_path, sop_source, root)

    assert labels == []
    assert unterkategorie == CATEGORY_LABELS["sop"]


def test_max_depth_truncation(leitlinien_source):
    root = Path("/data/2_Leitlinien")
    parts = ["a", "b", "c", "d", "e"]
    file_path = root.joinpath(*parts) / "file.pdf"

    labels, unterkategorie = extract_hierarchical_labels(file_path, leitlinien_source, root)

    assert len(labels) == MAX_HIERARCHY_DEPTH
    assert labels == ["a", "b", "c", "d"]
    assert unterkategorie == "d"


def test_faecher_three_levels():
    source = SourceConfig(name="5_Fächer", path="../5_Fächer", category="faecher")
    root = Path("/data/5_Fächer")
    file_path = root / "Diabetologie" / "Type1" / "Complications" / "doc.pdf"

    labels, unterkategorie = extract_hierarchical_labels(file_path, source, root)

    assert labels == ["Diabetologie", "Type1", "Complications"]
    assert unterkategorie == "Complications"


def test_extract_tag_suggestions_delegates_to_tagging_service(monkeypatch):
    entry = MagicMock()
    expected = {
        "source_path": "/workspace/doc.pdf",
        "hierarchy_labels": ["Leitlinien"],
        "has_actionable_suggestions": True,
        "fachgebiete": [],
    }

    monkeypatch.setattr(
        "api.services.tagging_service.TaggingService.get_suggestions",
        lambda self, _entry: expected,
    )

    result = extract_tag_suggestions_for_entry(MagicMock(), entry)

    assert result == expected


def test_apply_proposals_skips_case_variant_hierarchy_label():
    """A humanized label matching stored state only by case must not re-link.

    Regression: VPS reconcile crashed with entry_ordner_label PK violation —
    stored hierarchy/label 'notfall', proposal 'Notfall' passed the
    case-sensitive guards, resolve_ordner_label matched case-insensitively,
    and the append re-INSERTed an existing junction row.
    """
    from types import SimpleNamespace

    from api.services.tagging_service import (
        TagDimension,
        TagProposal,
        TagSource,
        TaggingService,
    )

    entry = SimpleNamespace(
        source_hierarchy=["notfall"],
        ordner_labels=[SimpleNamespace(id=671, name="notfall")],
        fachgebiete=[],
        diagnosen=[],
        symptome=[],
        dokumenttyp=None,
        dokumenttyp_id=None,
        unterkategorie=None,
    )
    service = TaggingService(MagicMock())  # db must never be queried
    proposal = TagProposal(
        dimension=TagDimension.HIERARCHY, label="Notfall", source=TagSource.FOLDER
    )

    result = service.apply_proposals(entry, [proposal], merge=True)

    assert result.hierarchy_added == 0
    assert entry.source_hierarchy == ["notfall"]
    assert len(entry.ordner_labels) == 1
    service.db.query.assert_not_called()

"""Tests for unified tagging service."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from api.services.tagging_service import (
    FolderHierarchyStrategy,
    TagDimension,
    TaggingService,
    TagSource,
)
from config import SourceConfig


@pytest.fixture
def leitlinien_source():
    return SourceConfig(name="2_Leitlinien", path="../2_Leitlinien", category="leitlinien")


def test_folder_strategy_proposes_hierarchy_and_dokumenttyp(leitlinien_source):
    root = Path("/data/2_Leitlinien")
    file_path = root / "Primärversorgung" / "doc.pdf"
    strategy = FolderHierarchyStrategy()

    proposals = strategy.propose(file_path, leitlinien_source, root)

    dimensions = {p.dimension for p in proposals}
    assert TagDimension.DOKUMENTTYP in dimensions
    assert TagDimension.HIERARCHY in dimensions
    assert any(p.label == "Leitlinie" for p in proposals)


def test_apply_proposals_stores_hierarchy_metadata():
    db = MagicMock()
    entry = MagicMock()
    entry.fachgebiete = []
    entry.diagnosen = []
    entry.symptome = []
    entry.source_hierarchy = []

    from api.services.tagging_service import TagProposal

    service = TaggingService(db)
    result = service.apply_proposals(
        entry,
        [
            TagProposal(TagDimension.DOKUMENTTYP, "Leitlinie", TagSource.FOLDER),
            TagProposal(TagDimension.HIERARCHY, "Radiologie", TagSource.FOLDER),
            TagProposal(TagDimension.HIERARCHY, "Demenz", TagSource.FOLDER),
        ],
    )

    assert result.hierarchy_added == 2
    assert result.dokumenttyp_set is True
    assert entry.dokumenttyp == "Leitlinie"
    assert entry.source_hierarchy == ["Radiologie", "Demenz"]
    assert entry.unterkategorie == "Demenz"

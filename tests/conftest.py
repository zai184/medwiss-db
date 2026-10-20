"""Pytest configuration and shared fixtures for medwiss-db."""

import pytest


@pytest.fixture
def sample_entry_data():
    """Minimal valid entry data for tests."""
    return {
        "titel": "Test Entry",
        "inhalt": "# Test\n\nThis is test content.",
        "zusammenfassung": "A test summary.",
        "quelle": "Test Source",
        "dokumenttyp": "Fall",
        "schwierigkeit": "anfaenger",
    }

"""Duplicate detection system for medical file processing pipeline.

This module provides SHA-256 based duplicate file detection to prevent
re-importing the same content multiple times.

Duplicate Strategy Options:
- skip: Return None if duplicate found
- update: Return existing entry for update
- fail: Raise exception if duplicate found

The file_hash column stores SHA-256 hashes of imported files for fast
duplicate detection.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import KnowledgeEntry
from pipeline.batch_processor import calculate_file_hash

logger = logging.getLogger(__name__)


class DuplicateStrategy(Enum):
    """Strategy for handling detected duplicates."""

    SKIP = "skip"  # Return None, caller skips the file
    UPDATE = "update"  # Return existing entry for update
    FAIL = "fail"  # Raise exception


class DuplicateFileError(Exception):
    """Raised when a duplicate file is detected and strategy is FAIL."""

    def __init__(self, file_hash: str, existing_entry_id: int):
        self.file_hash = file_hash
        self.existing_entry_id = existing_entry_id
        super().__init__(
            f"Duplicate file detected (hash={file_hash}, existing_entry_id={existing_entry_id})"
        )


class DuplicateDetector:
    """Detects and manages duplicate files based on SHA-256 content hash.

    This class provides methods to:
    - Calculate file hashes
    - Check if a hash already exists in the database
    - Retrieve existing entries by hash
    - Mark files as processed by storing their hash

    Example:
        >>> from api.database import get_db_context
        >>> with get_db_context() as db:
        ...     detector = DuplicateDetector(db)
        ...     hash_val = detector.calculate_hash("/path/to/file.jpg")
        ...     if detector.is_duplicate(hash_val):
        ...         existing = detector.get_existing_entry(hash_val)
        ...         print(f"Duplicate of entry {existing.id}")
        ...     else:
        ...         # Import the new file
        ...         detector.mark_as_processed("/path/to/file.jpg", new_entry_id)
    """

    def __init__(self, db: Session, strategy: DuplicateStrategy = DuplicateStrategy.SKIP):
        """Initialize the duplicate detector.

        Args:
            db: SQLAlchemy database session
            strategy: How to handle duplicates (skip/update/fail)
        """
        self.db = db
        self.strategy = strategy

    def calculate_hash(self, file_path: Union[str, Path]) -> str:
        """Calculate SHA-256 hash of a file.

        This is a convenience wrapper around calculate_file_hash from
        batch_processor module.

        Args:
            file_path: Path to the file to hash

        Returns:
            SHA-256 hash as hexadecimal string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        return calculate_file_hash(file_path)

    def is_duplicate(self, file_hash: str) -> bool:
        """Check if a file hash already exists in the database.

        Args:
            file_hash: SHA-256 hash to check

        Returns:
            True if an entry with this hash exists, False otherwise
        """
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.file_hash == file_hash)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result is not None

    def get_existing_entry(self, file_hash: str) -> Optional[KnowledgeEntry]:
        """Get the existing entry for a file hash.

        Args:
            file_hash: SHA-256 hash to look up

        Returns:
            KnowledgeEntry if found, None otherwise
        """
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.file_hash == file_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def mark_as_processed(self, file_path: Union[str, Path], entry_id: int) -> str:
        """Store the file hash after successful import.

        Call this after creating or updating a KnowledgeEntry to record
        the file's hash, enabling future duplicate detection.

        Args:
            file_path: Path to the processed file
            entry_id: ID of the created/updated KnowledgeEntry

        Returns:
            The calculated file hash

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If entry_id doesn't exist in database
        """
        file_hash = self.calculate_hash(file_path)

        stmt = select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        entry = self.db.execute(stmt).scalar_one_or_none()
        if entry is None:
            raise ValueError(f"KnowledgeEntry with id={entry_id} not found")

        entry.file_hash = file_hash
        self.db.commit()

        logger.info(f"Marked file {file_path} as processed with hash {file_hash}")
        return file_hash

    def check_and_handle(self, file_path: Union[str, Path]) -> Optional[KnowledgeEntry]:
        """Check for duplicate and handle according to strategy.

        This is a convenience method that combines hash calculation,
        duplicate detection, and strategy-based handling in one call.

        Args:
            file_path: Path to the file to check

        Returns:
            - None if strategy is SKIP or file is not a duplicate
            - Existing KnowledgeEntry if strategy is UPDATE and file is duplicate
            - Never returns if strategy is FAIL (raises instead)

        Raises:
            DuplicateFileError: If strategy is FAIL and duplicate found
            FileNotFoundError: If file doesn't exist
        """
        file_hash = self.calculate_hash(file_path)

        if not self.is_duplicate(file_hash):
            return None

        existing_entry = self.get_existing_entry(file_hash)

        if self.strategy == DuplicateStrategy.FAIL:
            if existing_entry is None:
                logger.error(
                    f"is_duplicate=True but get_existing_entry returned None for hash {file_hash}"
                )
                raise RuntimeError(f"Duplicate detection inconsistency for hash {file_hash}")
            raise DuplicateFileError(file_hash, existing_entry.id)

        if self.strategy == DuplicateStrategy.UPDATE:
            logger.info(
                f"Duplicate detected (hash={file_hash}), returning existing entry for update"
            )
            return existing_entry

        logger.info(f"Duplicate detected (hash={file_hash}), skipping")
        return None

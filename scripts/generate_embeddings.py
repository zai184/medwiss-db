#!/usr/bin/env python3
"""Batch embedding generation script for medical knowledge entries.

This script generates embeddings for all knowledge entries that don't have one yet.
Embeddings are generated using local llamaserver and stored in PostgreSQL with pgvector.

NO real-time generation - all embeddings are pre-computed in batch for performance.

Usage:
    python -m scripts.generate_embeddings
    python -m scripts.generate_embeddings --force  # Regenerate all embeddings
    python -m scripts.generate_embeddings --dry-run  # Show what would be done
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from api.config import settings
from pipeline.embeddings import (
    EmbeddingError,
    LlamaserverConnectionError,
    generate_embedding,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_llamaserver() -> bool:
    """Check if llamaserver is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.llamaserver_url}/health")
            return response.status_code == 200
    except Exception:
        return False


def get_entries_without_embeddings(session) -> list[dict]:
    """Get all knowledge entries that don't have embeddings yet."""
    query = text("""
        SELECT id, titel, zusammenfassung, inhalt
        FROM knowledge_entries
        WHERE embedding IS NULL
        ORDER BY id
    """)
    result = session.execute(query)
    return [
        {
            "id": row.id,
            "titel": row.titel,
            "zusammenfassung": row.zusammenfassung or "",
            "inhalt": row.inhalt,
        }
        for row in result
    ]


def get_all_entries(session) -> list[dict]:
    """Get all knowledge entries."""
    query = text("""
        SELECT id, titel, zusammenfassung, inhalt
        FROM knowledge_entries
        ORDER BY id
    """)
    result = session.execute(query)
    return [
        {
            "id": row.id,
            "titel": row.titel,
            "zusammenfassung": row.zusammenfassung or "",
            "inhalt": row.inhalt,
        }
        for row in result
    ]


def prepare_text_for_embedding(entry: dict) -> str:
    """Prepare entry text for embedding generation.

    Combines title, summary, and content for comprehensive semantic representation.
    """
    parts = []

    # Add title with high weight (repeat it)
    if entry["titel"]:
        parts.extend([entry["titel"], entry["titel"]])

    # Add summary
    if entry["zusammenfassung"]:
        parts.append(entry["zusammenfassung"])

    # Add truncated content (first 2000 chars for balance)
    if entry["inhalt"]:
        parts.append(entry["inhalt"][:2000])

    return "\n\n".join(parts)


def update_entry_embedding(session, entry_id: int, embedding: list[float]) -> None:
    """Update embedding for a knowledge entry."""
    query = text("""
        UPDATE knowledge_entries
        SET embedding = :embedding
        WHERE id = :entry_id
    """)
    session.execute(
        query,
        {"entry_id": entry_id, "embedding": str(embedding)},
    )


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for knowledge entries")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate embeddings for all entries (not just missing ones)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of entries to process before committing (default: 10)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of entries to process (for testing)",
    )

    args = parser.parse_args()

    # Check llamaserver connectivity
    logger.info(f"Checking llamaserver at {settings.llamaserver_url}...")
    if not check_llamaserver():
        logger.error(
            "Cannot connect to llamaserver. Please ensure it's running at "
            f"{settings.llamaserver_url}"
        )
        sys.exit(1)
    logger.info("llamaserver is reachable")

    # Setup database connection
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get entries to process
        if args.force:
            entries = get_all_entries(session)
            logger.info(f"Found {len(entries)} total entries (force mode)")
        else:
            entries = get_entries_without_embeddings(session)
            logger.info(f"Found {len(entries)} entries without embeddings")

        if args.limit:
            entries = entries[: args.limit]
            logger.info(f"Limited to {len(entries)} entries")

        if not entries:
            logger.info("No entries to process. Exiting.")
            return

        if args.dry_run:
            logger.info(f"DRY RUN: Would process {len(entries)} entries")
            for entry in entries[:5]:
                logger.info(f"  - Entry {entry['id']}: {entry['titel'][:50]}...")
            if len(entries) > 5:
                logger.info(f"  ... and {len(entries) - 5} more")
            return

        # Process entries
        success_count = 0
        error_count = 0

        with tqdm(total=len(entries), desc="Generating embeddings") as pbar:
            for i, entry in enumerate(entries):
                try:
                    # Prepare text
                    text = prepare_text_for_embedding(entry)

                    # Generate embedding
                    embedding = generate_embedding(text)

                    # Update database
                    update_entry_embedding(session, entry["id"], embedding)

                    success_count += 1

                    # Commit in batches
                    if (i + 1) % args.batch_size == 0:
                        session.commit()
                        logger.debug(f"Committed batch of {args.batch_size} entries")

                except LlamaserverConnectionError as e:
                    logger.error(f"Connection error for entry {entry['id']}: {e}")
                    error_count += 1
                    # Continue with next entry

                except EmbeddingError as e:
                    logger.error(f"Embedding error for entry {entry['id']}: {e}")
                    error_count += 1
                    # Continue with next entry

                except Exception as e:
                    logger.error(
                        f"Unexpected error for entry {entry['id']}: {e}",
                        exc_info=True,
                    )
                    error_count += 1
                    # Continue with next entry

                finally:
                    pbar.update(1)

        # Final commit for remaining entries
        session.commit()

        # Summary
        logger.info("=" * 50)
        logger.info("Batch embedding generation complete")
        logger.info(f"  Total entries: {len(entries)}")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info("=" * 50)

        if error_count > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Committing processed entries...")
        session.commit()
        sys.exit(130)

    finally:
        session.close()


if __name__ == "__main__":
    main()

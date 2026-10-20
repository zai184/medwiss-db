#!/usr/bin/env python3
"""Load AWMF chunks + documents from the Leitlinien embedding KB into medwiss-db pgvector.

Reads the Leitlinien artifacts (chunks.jsonl + vectors.f32 + vector_ids.jsonl + meta.sqlite)
and INSERTs into medwiss-db's `chunks` (source_type='awmf') + `awmf_documents` tables.
Vectors are bit-identical to the FAISS index (same Qwen3-8B Q6_K, slice→normalize to 2048) —
no re-embedding happens here.

Usage:
    python -m scripts.import_awmf_chunks                    # LEITLINIEN_DATA autodetect
    python -m scripts.import_awmf_chunks --data ~/Projekte/embeddings/Leitlinien/data
    python -m scripts.import_awmf_chunks --truncate         # wipe chunks/awmf_documents first

Verification after load:
    SELECT count(*) FROM chunks WHERE source_type='awmf';   -- 594_079
    SELECT count(*) FROM awmf_documents;                    -- 1_886
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from api.config import settings
from api.database import engine
from database.models import AWMADocument, Chunk

logger = logging.getLogger(__name__)

DEFAULT_DATA = Path.home() / "Projekte/embeddings/Leitlinien/data"
CHUNK_BATCH = 2000


def parse_seq(chunk_id: str) -> int:
    """Chunk id format: '{awmf}_{seq:04d}' → seq."""
    try:
        return int(chunk_id.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        return 0


def load_awmf_documents(db, chunks_file: Path, doc_id_by_path: dict[str, int]) -> None:
    """Register one awmf_document per unique chunk path (authoritative awmf/title/society from
    chunks.jsonl — meta.sqlite pdfs.awmf holds malformed filename-prefix values)."""
    docs: dict[str, dict] = {}
    for line in chunks_file.open():
        c = json.loads(line)
        p = c["path"]
        if p not in docs:
            docs[p] = {"awmf": c.get("awmf") or "", "title": c.get("title") or "",
                       "society": c.get("society") or ""}
    for path, d in docs.items():
        existing = db.query(AWMADocument).filter(AWMADocument.path == path).first()
        if existing:
            doc_id_by_path[path] = existing.id
            continue
        doc = AWMADocument(awmf=d["awmf"], title=d["title"], society=d["society"], path=path)
        db.add(doc)
        db.flush()  # assigns doc.id
        doc_id_by_path[path] = doc.id
    db.commit()
    logger.info("awmf_documents: %d registered", len(doc_id_by_path))


def load_chunks(db, data_dir: Path, doc_id_by_path: dict[str, int]) -> None:
    """Stream chunks.jsonl + vectors.f32 (memmap, aligned) into the chunks table."""
    chunks_file = data_dir / "chunks.jsonl"
    vids_file = data_dir / "vector_ids.jsonl"
    vecs_file = data_dir / "vectors.f32"

    chunk_lines = chunks_file.open()
    vid_lines = [json.loads(line)["id"] for line in vids_file.open()]
    n_vec = vecs_file.stat().st_size // (settings.embedding_dimension * 4)
    vecs = np.memmap(vecs_file, dtype=np.float32, mode="r",
                     shape=(n_vec, settings.embedding_dimension))

    if len(vid_lines) != n_vec:
        raise RuntimeError(
            f"vector_ids ({len(vid_lines)}) != vectors rows ({n_vec}) — abort"
        )

    inserted = 0
    batch = []
    db.commit()  # doc inserts are already committed
    row_by_id = {cid: i for i, cid in enumerate(vid_lines)}
    for line in chunk_lines:
        c = json.loads(line)
        chunk_id = c["id"]
        row_idx = row_by_id.get(chunk_id)
        if row_idx is None:
            logger.warning("chunk id %s not in vector_ids — skipped", chunk_id)
            continue
        doc_id = doc_id_by_path.get(c["path"])
        if doc_id is None:
            logger.warning("no awmf_document for path %s — skipped", c["path"])
            continue
        batch.append(
            {
                "source_type": "awmf",
                "source_id": doc_id,
                "source_path": c["path"],
                "title": c["title"],
                "awmf": c.get("awmf") or "",
                "society": c.get("society") or "",
                "page": c.get("page"),
                "seq": parse_seq(chunk_id),
                "text": c["text"].replace("\x00", ""),   # psycopg2 rejects NUL bytes,
                "embedding": vecs[row_idx].tolist(),
            }
        )
        if len(batch) >= CHUNK_BATCH:
            db.bulk_insert_mappings(Chunk, batch)
            db.commit()
            inserted += len(batch)
            batch = []
            logger.info("chunks inserted: %d", inserted)

    if batch:
        db.bulk_insert_mappings(Chunk, batch)
        db.commit()
        inserted += len(batch)
    logger.info("total chunks inserted: %d", inserted)


def build_hnsw_index() -> None:
    """HNSW index skipped: pgvector HNSW caps at 2000 dims; vectors are 2048.

    Exact scan via the `vector_cosine_ops` `<->` operator is used instead (~594k x 2048
    cosine, well within query-time budget). Details: plans/awmf-foldin-dashboard.md.
    """
    logger.info("HNSW index skipped (2048 dims exceed pgvector 2000-dim HNSW cap); exact scan used")


def main() -> None:
    ap = argparse.ArgumentParser(description="Load AWMF chunks into medwiss-db pgvector")
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Leitlinien data dir")
    ap.add_argument("--truncate", action="store_true", help="Wipe chunks/awmf_documents first")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not (args.data / "chunks.jsonl").exists():
        raise SystemExit(f"data dir missing chunks.jsonl: {args.data}")

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        if args.truncate:
            db.execute(sa.text("DELETE FROM chunks"))
            db.execute(sa.text("DELETE FROM awmf_documents"))
            db.commit()
            logger.info("truncated chunks + awmf_documents")

        # Skip if already loaded
        loaded = db.query(Chunk).filter(Chunk.source_type == "awmf").count()
        if loaded > 0:
            raise SystemExit(
                f"chunks already has {loaded} awmf rows — use --truncate to reload"
            )

        doc_id_by_path: dict[str, int] = {}
        load_awmf_documents(db, args.data / "chunks.jsonl", doc_id_by_path)
        load_chunks(db, args.data, doc_id_by_path)
        build_hnsw_index()
    finally:
        db.close()

    # Final integrity check
    with engine.connect() as conn:
        n = conn.execute(
            sa.text("SELECT count(*) FROM chunks WHERE source_type='awmf'")
        ).scalar()
        nd = conn.execute(sa.text("SELECT count(*) FROM awmf_documents")).scalar()
    logger.info("DONE — chunks=%d awmf_documents=%d", n, nd)


if __name__ == "__main__":
    main()

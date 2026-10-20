"""Database models for the medical knowledge database."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base

class AWMADocument(Base):
    """AWMF guideline document registry (one row per PDF)."""

    __tablename__ = "awmf_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    awmf: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    society: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk",
        primaryjoin="and_(Chunk.source_type=='awmf', foreign(Chunk.source_id)==AWMADocument.id)",
        viewonly=True,
    )


class Chunk(Base):
    """Universal chunk store (library + AWMF); polymorphic source via (source_type, source_id)."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    awmf: Mapped[Optional[str]] = mapped_column(Text)
    society: Mapped[Optional[str]] = mapped_column(Text)
    page: Mapped[Optional[int]] = mapped_column(Integer)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(2048), nullable=False)
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


# Association tables for many-to-many relationships
entry_fach_table = Table(
    "entry_fach",
    Base.metadata,
    Column(
        "entry_id",
        Integer,
        ForeignKey("knowledge_entries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("fach_id", Integer, ForeignKey("fachgebiete.id", ondelete="CASCADE"), primary_key=True),
)

entry_symptom_table = Table(
    "entry_symptom",
    Base.metadata,
    Column(
        "entry_id",
        Integer,
        ForeignKey("knowledge_entries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("symptom_id", Integer, ForeignKey("symptome.id", ondelete="CASCADE"), primary_key=True),
)

entry_diagnose_table = Table(
    "entry_diagnose",
    Base.metadata,
    Column(
        "entry_id",
        Integer,
        ForeignKey("knowledge_entries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "diagnose_id", Integer, ForeignKey("diagnosen.id", ondelete="CASCADE"), primary_key=True
    ),
)

entry_ordner_label_table = Table(
    "entry_ordner_label",
    Base.metadata,
    Column(
        "entry_id",
        Integer,
        ForeignKey("knowledge_entries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "label_id", Integer, ForeignKey("ordner_labels.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Fachgebiet(Base):
    """Medical specialty/field."""

    __tablename__ = "fachgebiete"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    beschreibung: Mapped[Optional[str]] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    entries: Mapped[List["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry",
        secondary=entry_fach_table,
        back_populates="fachgebiete",
    )


class Diagnose(Base):
    """Medical diagnosis (ICD-10 based)."""

    __tablename__ = "diagnosen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    beschreibung: Mapped[Optional[str]] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)
    icd11_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    entries: Mapped[List["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry",
        secondary=entry_diagnose_table,
        back_populates="diagnosen",
    )


class OrdnerLabel(Base):
    """Ordner label (folder label for organizing knowledge entries)."""

    __tablename__ = "ordner_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    entries: Mapped[List["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry",
        secondary=entry_ordner_label_table,
        back_populates="ordner_labels",
    )


class Dokumenttyp(Base):
    """Document type of a knowledge entry."""

    __tablename__ = "dokumenttypen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    entries: Mapped[List["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry",
        back_populates="dokumenttyp_ref",
    )


class Symptom(Base):
    """Medical symptom."""

    __tablename__ = "symptome"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    beschreibung: Mapped[Optional[str]] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    entries: Mapped[List["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry",
        secondary=entry_symptom_table,
        back_populates="symptome",
    )


class User(Base):
    """User account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    vorname: Mapped[Optional[str]] = mapped_column(String(100))
    nachname: Mapped[Optional[str]] = mapped_column(String(100))
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))



class KnowledgeEntry(Base):
    """Main knowledge entry/article."""

    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titel: Mapped[str] = mapped_column(String(500), nullable=False)
    zusammenfassung: Mapped[Optional[str]] = mapped_column(Text)
    inhalt: Mapped[str] = mapped_column(Text, nullable=False)
    quelle: Mapped[Optional[str]] = mapped_column(String(500))
    schwierigkeit: Mapped[Optional[str]] = mapped_column(String(20))
    unterkategorie: Mapped[Optional[str]] = mapped_column(String(100))
    dokumenttyp_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("dokumenttypen.id", ondelete="SET NULL"), nullable=True
    )
    dokumenttyp: Mapped[Optional[str]] = mapped_column(String(50))
    source_hierarchy: Mapped[list] = mapped_column(JSONB, default=list)
    source_path: Mapped[Optional[str]] = mapped_column(Text)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )

    # Relationships
    fachgebiete: Mapped[List["Fachgebiet"]] = relationship(
        "Fachgebiet",
        secondary=entry_fach_table,
        back_populates="entries",
    )
    diagnosen: Mapped[List["Diagnose"]] = relationship(
        "Diagnose",
        secondary=entry_diagnose_table,
        back_populates="entries",
    )
    symptome: Mapped[List["Symptom"]] = relationship(
        "Symptom",
        secondary=entry_symptom_table,
        back_populates="entries",
    )
    ordner_labels: Mapped[List["OrdnerLabel"]] = relationship(
        "OrdnerLabel",
        secondary=entry_ordner_label_table,
        back_populates="entries",
    )
    dokumenttyp_ref: Mapped[Optional["Dokumenttyp"]] = relationship(
        "Dokumenttyp",
        back_populates="entries",
    )

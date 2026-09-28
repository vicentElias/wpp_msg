"""Persistência de contatos: PostgreSQL configurado por DATABASE_URL ou SQLite local."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from sqlalchemy import Integer, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parent
LEGACY_IMPORT_KEY = "legacy_contacts_imported_v1"
PHONE_PATTERN = re.compile(r"\+\d{10,15}")


class Base(DeclarativeBase):
    pass


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    telefone: Mapped[str] = mapped_column(String(16), nullable=False)


class AppMetadata(Base):
    __tablename__ = "app_metadata"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


def normalize_database_url(url: str) -> str:
    """Use the psycopg 3 SQLAlchemy dialect for standard PostgreSQL URLs."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def create_database_engine(database_url: str | None = None) -> Engine:
    """Build an engine from DATABASE_URL, defaulting to an ignored local SQLite file."""
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        data_dir = Path(os.environ.get("APP_DATA_DIR", ROOT / "data"))
        data_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{(data_dir / 'contacts.sqlite3').as_posix()}"

    url = normalize_database_url(url)
    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **options)


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _legacy_contacts() -> list[dict[str, str]]:
    """Read active entries only; commented-out entries were never live app contacts."""
    try:
        from contato import CONTATOS
    except (ImportError, AttributeError):
        return []

    contacts: list[dict[str, str]] = []
    for item in CONTATOS:
        nome = str(item.get("nome", "")).strip()
        telefone = str(item.get("telefone", "")).strip()
        if nome and PHONE_PATTERN.fullmatch(telefone):
            contacts.append({"nome": nome, "telefone": telefone})
    return contacts


def initialize_database(target_engine: Engine = engine) -> int:
    """Create tables and import the legacy list once; return imported row count."""
    Base.metadata.create_all(target_engine)
    factory = sessionmaker(bind=target_engine, expire_on_commit=False)
    imported = 0

    with factory.begin() as session:
        migration = session.get(AppMetadata, LEGACY_IMPORT_KEY)
        if migration is None:
            has_contacts = session.scalar(select(Contact.id).limit(1)) is not None
            legacy = [] if has_contacts else _legacy_contacts()
            session.add_all(Contact(**item) for item in legacy)
            session.add(AppMetadata(key=LEGACY_IMPORT_KEY, value=str(len(legacy))))
            imported = len(legacy)
    return imported


def list_contacts() -> list[dict[str, object]]:
    with SessionLocal() as session:
        rows = session.scalars(select(Contact).order_by(Contact.nome, Contact.id)).all()
        return [
            {"id": row.id, "nome": row.nome, "telefone": row.telefone}
            for row in rows
        ]


def create_contact(nome: str, telefone: str) -> dict[str, object]:
    with SessionLocal.begin() as session:
        row = Contact(nome=nome, telefone=telefone)
        session.add(row)
        session.flush()
        return {"id": row.id, "nome": row.nome, "telefone": row.telefone}


def update_contact(contact_id: int, nome: str, telefone: str) -> dict[str, object] | None:
    with SessionLocal.begin() as session:
        row = session.get(Contact, contact_id)
        if row is None:
            return None
        row.nome = nome
        row.telefone = telefone
        session.flush()
        return {"id": row.id, "nome": row.nome, "telefone": row.telefone}


def delete_contact(contact_id: int) -> bool:
    with SessionLocal.begin() as session:
        row = session.get(Contact, contact_id)
        if row is None:
            return False
        session.delete(row)
        return True

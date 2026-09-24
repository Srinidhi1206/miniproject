"""Safety Center guides. Seeded from `backend/knowledge/*.md` — the same corpus
the RAG layer retrieves from, so what users read and what explanations cite
are always consistent."""

from __future__ import annotations

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SafetyGuide(Base):
    __tablename__ = "safety_guides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(48), index=True)
    summary: Mapped[str] = mapped_column(Text)
    body_markdown: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    read_minutes: Mapped[int] = mapped_column(Integer, default=2)
    order: Mapped[int] = mapped_column(Integer, default=0)

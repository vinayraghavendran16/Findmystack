from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tool_name: Mapped[str] = mapped_column(String(200), index=True)
    vendor_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    hits: Mapped[list["Hit"]] = relationship(back_populates="search", cascade="all, delete-orphan")


class Hit(Base):
    """A raw candidate mention pulled from a provider before verification."""

    __tablename__ = "hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("searches.id"), index=True)
    provider: Mapped[str] = mapped_column(String(60), index=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    candidate_company: Mapped[str | None] = mapped_column(String(300), nullable=True)
    raw_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    search: Mapped[Search] = relationship(back_populates="hits")
    confirmation: Mapped["Confirmation | None"] = relationship(back_populates="hit", uselist=False)


class Confirmation(Base):
    """LLM-verified match between a company and a tool, backed by a Hit."""

    __tablename__ = "confirmations"
    __table_args__ = (
        UniqueConstraint("tool_name_norm", "company_norm", "source_url", name="uq_conf_tool_company_url"),
        Index("ix_conf_tool_company", "tool_name_norm", "company_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hit_id: Mapped[int] = mapped_column(ForeignKey("hits.id"), unique=True)
    tool_name: Mapped[str] = mapped_column(String(200))
    tool_name_norm: Mapped[str] = mapped_column(String(200), index=True)
    company: Mapped[str] = mapped_column(String(300))
    company_norm: Mapped[str] = mapped_column(String(300), index=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(60))
    evidence_snippet: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    verified: Mapped[bool] = mapped_column(default=True)
    verifier_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    hit: Mapped[Hit] = relationship(back_populates="confirmation")


def normalize(s: str) -> str:
    return " ".join(s.lower().split())

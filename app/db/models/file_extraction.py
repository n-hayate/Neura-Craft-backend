from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class FileExtraction(Base):
    __tablename__ = "file_extractions"
    __table_args__ = (UniqueConstraint("file_id", name="uq_file_extractions_file_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("files.id"),
        nullable=False,
        index=True,
    )

    # 抽出結果（meta/log/formulation/derivedなど）
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )




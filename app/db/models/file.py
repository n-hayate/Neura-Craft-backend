from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True,
    )
    blob_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(Unicode(255), nullable=False)

    application: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    issue: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    ingredient: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    customer: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    trial_id: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    author: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner = relationship("User", backref="files")

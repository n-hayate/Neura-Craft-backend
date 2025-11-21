from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_name: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    azure_blob_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # メタデータフィールド
    final_product: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    issue: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ingredient: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trial_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    owner = relationship("User", backref="files")



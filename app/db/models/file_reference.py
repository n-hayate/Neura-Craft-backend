from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FileReference(Base):
    __tablename__ = "file_references"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), nullable=False)
    trial_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file = relationship("File", backref="references")
    user = relationship("User", backref="file_references")

    __table_args__ = (
        UniqueConstraint('file_id', 'user_id', 'trial_id', name='uix_file_user_trial'),
    )


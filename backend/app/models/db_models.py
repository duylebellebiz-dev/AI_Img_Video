import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|completed|failed|cancelled
    pairing_mode: Mapped[str] = mapped_column(String(20))  # cross|random|one_to_one
    num_images: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")

    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    design_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    pose_paths: Mapped[list[str]] = mapped_column(JSON, default=list)

    progress_completed: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)

    zip_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    images: Mapped[list["GeneratedImage"]] = relationship(
        back_populates="batch_job", cascade="all, delete-orphan"
    )


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_job_id: Mapped[str] = mapped_column(ForeignKey("batch_jobs.id"))

    design_filename: Mapped[str] = mapped_column(String(255))
    pose_filename: Mapped[str] = mapped_column(String(255))
    original_design_path: Mapped[str] = mapped_column(String(500))
    original_pose_path: Mapped[str] = mapped_column(String(500))
    variation: Mapped[int] = mapped_column(Integer, default=1)

    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    passed: Mapped[bool] = mapped_column(default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|generating|passed|needs_review|cancelled

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    batch_job: Mapped["BatchJob"] = relationship(back_populates="images")


class EditJob(Base):
    """A multi-image AI edit batch: the same edit instruction is applied to
    every uploaded photo (see CLAUDE.md #2 — this is Module 1's edit sibling,
    not a new module). Mirrors BatchJob's status/progress/zip shape so the
    frontend can reuse the same polling pattern."""

    __tablename__ = "edit_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|completed|failed|cancelled
    prompt: Mapped[str] = mapped_column(Text)

    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    apply_logo: Mapped[bool] = mapped_column(default=False)

    progress_completed: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)

    zip_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    edits: Mapped[list["ImageEdit"]] = relationship(back_populates="edit_job", cascade="all, delete-orphan")


class ImageEdit(Base):
    """Single-photo AI edit: upload one image + a freeform instruction, get back
    an edited image. Separate from BatchJob's design+pose pairing flow.
    edit_job_id is null for the original single-photo endpoint and set when
    the edit belongs to a multi-image EditJob batch."""

    __tablename__ = "image_edits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    edit_job_id: Mapped[str | None] = mapped_column(ForeignKey("edit_jobs.id"), nullable=True)

    original_filename: Mapped[str] = mapped_column(String(255))
    original_path: Mapped[str] = mapped_column(String(500), default="")

    prompt: Mapped[str] = mapped_column(Text)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing|completed|failed|cancelled
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    edit_job: Mapped["EditJob | None"] = relationship(back_populates="edits")


class ScheduledPost(Base):
    """Draft-only placeholder so campaign data has a home once captions/hashtags/
    scheduling exist (Phase 2+). PublishingService only ever writes 'draft' rows
    here — see app/services/publishing_service.py. No real publishing happens.
    """

    __tablename__ = "scheduled_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_job_id: Mapped[str] = mapped_column(ForeignKey("batch_jobs.id"))
    image_id: Mapped[str | None] = mapped_column(ForeignKey("generated_images.id"), nullable=True)

    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    suggested_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SalonBranding(Base):
    """Singleton row (always id=SINGLETON_ID) holding the salon's logo, used
    to watermark generated/edited images. No multi-tenant support yet — one
    salon per deployment, per CLAUDE.md #8 (no multi-user/billing logic)."""

    __tablename__ = "salon_branding"

    SINGLETON_ID = "default"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: SalonBranding.SINGLETON_ID)
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

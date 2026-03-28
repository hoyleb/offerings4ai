from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LicenseType(enum.StrEnum):
    EXCLUSIVE_TRANSFER = "exclusive_transfer"
    NON_EXCLUSIVE = "non_exclusive"
    REVENUE_SHARE = "revenue_share"
    PUBLIC_DOMAIN = "public_domain"


class IdeaStatus(enum.StrEnum):
    QUEUED = "queued"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PAID = "paid"


class SubmissionCategory(enum.StrEnum):
    AGENT_WORKFLOW = "agent_workflow"
    PRODUCT = "product"
    AUTOMATION = "automation"
    RESEARCH = "research"
    CREATIVE = "creative"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    payout_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    email_verification_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    email_verification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    password_reset_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    password_reset_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    ideas: Mapped[list[Idea]] = relationship(
        "Idea",
        back_populates="creator",
        cascade="all,delete-orphan",
    )

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None


class Idea(Base):
    __tablename__ = "ideas"
    __table_args__ = (UniqueConstraint("content_fingerprint", name="uq_idea_fingerprint"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[SubmissionCategory] = mapped_column(Enum(SubmissionCategory))
    problem: Mapped[str] = mapped_column(Text)
    proposed_idea: Mapped[str] = mapped_column(Text)
    why_ai_benefits: Mapped[str] = mapped_column(Text)
    expected_reward_range: Mapped[str | None] = mapped_column(String(64), nullable=True)
    license_type: Mapped[LicenseType] = mapped_column(Enum(LicenseType))
    status: Mapped[IdeaStatus] = mapped_column(
        Enum(IdeaStatus),
        default=IdeaStatus.QUEUED,
        index=True,
    )
    score_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ownership_record: Mapped[str] = mapped_column(Text)
    content_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_flagged_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    creator: Mapped[User] = relationship("User", back_populates="ideas")
    evaluations: Mapped[list[Evaluation]] = relationship(
        "Evaluation",
        back_populates="idea",
        cascade="all,delete-orphan",
    )
    payout: Mapped[Payout | None] = relationship(
        "Payout",
        back_populates="idea",
        uselist=False,
        cascade="all,delete-orphan",
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    idea_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ideas.id"), index=True)
    evaluator_version: Mapped[str] = mapped_column(String(64), default="mock-v1")
    novelty_score: Mapped[int] = mapped_column(Integer)
    clarity_score: Mapped[int] = mapped_column(Integer)
    utility_score: Mapped[int] = mapped_column(Integer)
    leverage_score: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[int] = mapped_column(Integer, index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    idea: Mapped[Idea] = relationship("Idea", back_populates="evaluations")


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    idea_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ideas.id"), unique=True)
    gross_amount: Mapped[float] = mapped_column(Float)
    fee_amount: Mapped[float] = mapped_column(Float)
    net_amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(12), default="USD")
    provider: Mapped[str] = mapped_column(String(64), default="simulated")
    transaction_reference: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    idea: Mapped[Idea] = relationship("Idea", back_populates="payout")

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import IdeaStatus, LicenseType, SubmissionCategory


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    payout_address: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    payout_address: str | None
    reputation_score: float
    is_email_verified: bool
    email_verified_at: datetime | None
    created_at: datetime


class VerificationDispatchResponse(BaseModel):
    message: str
    debug_verify_url: str | None = None
    debug_verify_token: str | None = None


class RegistrationResponse(VerificationDispatchResponse):
    user: UserPublic
    requires_email_verification: bool = True


class IdeaCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    category: SubmissionCategory
    problem: str = Field(min_length=20, max_length=5000)
    proposed_idea: str = Field(min_length=20, max_length=10000)
    why_ai_benefits: str = Field(min_length=20, max_length=5000)
    expected_reward_range: str | None = Field(default=None, max_length=64)
    license_type: LicenseType


class EvaluationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evaluator_version: str
    novelty_score: int
    clarity_score: int
    utility_score: int
    leverage_score: int
    total_score: int
    decision: str
    rationale: str
    created_at: datetime


class PayoutPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gross_amount: float
    fee_amount: float
    net_amount: float
    currency: str
    provider: str
    transaction_reference: str
    status: str
    created_at: datetime


class IdeaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    category: SubmissionCategory
    problem: str
    proposed_idea: str
    why_ai_benefits: str
    expected_reward_range: str | None
    license_type: LicenseType
    status: IdeaStatus
    score_total: int | None
    ownership_record: str
    content_fingerprint: str
    feedback: str | None
    similarity_score: float | None
    is_flagged_duplicate: bool
    created_at: datetime
    updated_at: datetime
    evaluations: list[EvaluationPublic] = []
    payout: PayoutPublic | None = None


class DashboardSummary(BaseModel):
    total_submissions: int
    accepted_count: int
    rejected_count: int
    paid_count: int
    total_net_rewards: float
    average_score: float


class HealthResponse(BaseModel):
    status: str
    queue_mode: str
    app_env: str


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=16, max_length=255)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationResponse(BaseModel):
    message: str

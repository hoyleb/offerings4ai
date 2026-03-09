from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Idea, IdeaStatus, LicenseType, User
from app.schemas import DashboardSummary, IdeaCreate
from app.services.fingerprints import generate_idea_fingerprint, jaccard_similarity
from app.services.queue import get_queue
from app.services.safety import enforce_safe_submission


def build_ownership_record(user: User, license_type: LicenseType) -> str:
    """Purpose: Build the legal ownership record stored against an idea.

    Args:
        user: Creator account that submitted the idea.
        license_type: Selected commercial rights model.

    Returns:
        Human-readable ownership record without exposing the creator email publicly.
    """

    return (
        f"Submitted by creator account {user.id} on {datetime.now(UTC).isoformat()} under license "
        f"{license_type.value}. Acceptance and payout bind the selected commercial terms."
    )


def enforce_submission_rate_limit(db: Session, user: User) -> None:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    recent_count = db.scalar(
        select(func.count(Idea.id)).where(Idea.creator_id == user.id, Idea.created_at >= cutoff)
    )
    if recent_count and recent_count >= settings.max_submissions_per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Hourly submission limit reached",
        )


def _find_similarity(db: Session, payload: IdeaCreate) -> tuple[float | None, bool]:
    settings = get_settings()
    existing_ideas = db.scalars(select(Idea)).all()
    if not existing_ideas:
        return None, False

    candidate_text = " ".join(
        [payload.title, payload.problem, payload.proposed_idea, payload.why_ai_benefits]
    )
    best = 0.0
    for idea in existing_ideas:
        existing_text = " ".join(
            [idea.title, idea.problem, idea.proposed_idea, idea.why_ai_benefits]
        )
        best = max(best, jaccard_similarity(candidate_text, existing_text))
    return round(best, 3), best >= settings.similarity_threshold


def enqueue_evaluation(idea_id: str) -> None:
    settings = get_settings()
    if settings.queue_mode == "inline":
        from app.worker import evaluate_idea_job

        evaluate_idea_job(idea_id)
        return

    queue = get_queue()
    queue.enqueue("app.worker.evaluate_idea_job", idea_id)


def create_idea(db: Session, user: User, payload: IdeaCreate) -> Idea:
    enforce_submission_rate_limit(db, user)
    enforce_safe_submission(payload)
    fingerprint = generate_idea_fingerprint(
        payload.title,
        payload.problem,
        payload.proposed_idea,
        payload.why_ai_benefits,
    )
    existing = db.scalar(select(Idea).where(Idea.content_fingerprint == fingerprint))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate idea fingerprint",
        )

    similarity_score, is_duplicate = _find_similarity(db, payload)
    idea = Idea(
        creator_id=user.id,
        title=payload.title.strip(),
        category=payload.category,
        problem=payload.problem.strip(),
        proposed_idea=payload.proposed_idea.strip(),
        why_ai_benefits=payload.why_ai_benefits.strip(),
        expected_reward_range=payload.expected_reward_range,
        license_type=payload.license_type,
        status=IdeaStatus.QUEUED,
        ownership_record=build_ownership_record(user, payload.license_type),
        content_fingerprint=fingerprint,
        similarity_score=similarity_score,
        is_flagged_duplicate=is_duplicate,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)

    enqueue_evaluation(str(idea.id))
    db.refresh(idea)
    return idea


def get_dashboard_summary(db: Session, user: User) -> DashboardSummary:
    ideas = db.scalars(select(Idea).where(Idea.creator_id == user.id)).all()
    total_submissions = len(ideas)
    accepted_statuses = {IdeaStatus.ACCEPTED, IdeaStatus.PAID}
    accepted_count = sum(1 for idea in ideas if idea.status in accepted_statuses)
    rejected_count = sum(1 for idea in ideas if idea.status == IdeaStatus.REJECTED)
    paid_count = sum(1 for idea in ideas if idea.status == IdeaStatus.PAID)
    total_net_rewards = sum(idea.payout.net_amount for idea in ideas if idea.payout)
    scores = [idea.score_total for idea in ideas if idea.score_total is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    return DashboardSummary(
        total_submissions=total_submissions,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        paid_count=paid_count,
        total_net_rewards=round(total_net_rewards, 2),
        average_score=average_score,
    )

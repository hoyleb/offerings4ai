from __future__ import annotations

from uuid import UUID

from redis import Redis
from rq import Worker
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import SessionLocal, ensure_current_schema
from app.models import Evaluation, Idea, IdeaStatus, Payout
from app.services.evaluator import build_evaluator
from app.services.payments import PaymentProcessor


def evaluate_idea_job(idea_id: str) -> None:
    with SessionLocal() as db:
        _evaluate_idea(db, UUID(idea_id))


def _evaluate_idea(db: Session, idea_id: UUID) -> None:
    idea = db.get(Idea, idea_id)
    if idea is None or idea.status not in {IdeaStatus.QUEUED, IdeaStatus.UNDER_REVIEW}:
        return

    idea.status = IdeaStatus.UNDER_REVIEW
    db.add(idea)
    db.commit()
    db.refresh(idea)

    result = build_evaluator().evaluate(idea)
    db.add(
        Evaluation(
            idea_id=idea.id,
            evaluator_version=result.evaluator_version,
            novelty_score=result.novelty_score,
            clarity_score=result.clarity_score,
            utility_score=result.utility_score,
            leverage_score=result.leverage_score,
            total_score=result.total_score,
            decision=result.decision,
            rationale=result.rationale,
        )
    )

    idea.score_total = result.total_score
    idea.feedback = result.rationale

    if result.decision == "accept" and result.reward_amount > 0:
        payment = PaymentProcessor().process(result.reward_amount)
        db.add(
            Payout(
                idea_id=idea.id,
                gross_amount=payment.gross_amount,
                fee_amount=payment.fee_amount,
                net_amount=payment.net_amount,
                currency=payment.currency,
                provider=payment.provider,
                transaction_reference=payment.transaction_reference,
                status=payment.status,
            )
        )
        idea.status = IdeaStatus.PAID
    elif result.decision == "accept":
        idea.status = IdeaStatus.ACCEPTED
    else:
        idea.status = IdeaStatus.REVIEWED

    db.add(idea)
    db.commit()


def run_worker() -> None:
    ensure_current_schema()
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    worker = Worker(["idea-evaluations"], connection=connection)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    run_worker()

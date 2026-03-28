from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_current_user, get_db
from app.models import Idea, User
from app.schemas import DashboardSummary, IdeaCreate, IdeaPublic
from app.services.ideas import create_idea, get_dashboard_summary

router = APIRouter(prefix="/ideas", tags=["ideas"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=IdeaPublic, status_code=status.HTTP_201_CREATED)
def submit_idea(payload: IdeaCreate, db: DbSession, current_user: CurrentUser) -> IdeaPublic:
    idea = create_idea(db, current_user, payload)
    statement = (
        select(Idea)
        .where(Idea.id == idea.id)
        .options(selectinload(Idea.evaluations), selectinload(Idea.payout))
    )
    refreshed = db.scalar(statement)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea not found")
    return refreshed


@router.get("/my/ideas", response_model=list[IdeaPublic])
def list_ideas(db: DbSession, current_user: CurrentUser) -> list[IdeaPublic]:
    statement = (
        select(Idea)
        .where(Idea.creator_id == current_user.id)
        .order_by(Idea.created_at.desc())
        .options(selectinload(Idea.evaluations), selectinload(Idea.payout))
    )
    return list(db.scalars(statement).unique().all())


@router.get("/my/ideas/dashboard", response_model=DashboardSummary)
def dashboard(db: DbSession, current_user: CurrentUser) -> DashboardSummary:
    return get_dashboard_summary(db, current_user)


@router.get("/my/ideas/{idea_id}", response_model=IdeaPublic)
def get_idea(idea_id: str, db: DbSession, current_user: CurrentUser) -> IdeaPublic:
    statement = (
        select(Idea)
        .where(Idea.id == idea_id, Idea.creator_id == current_user.id)
        .options(selectinload(Idea.evaluations), selectinload(Idea.payout))
    )
    idea = db.scalar(statement)
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea not found")
    return idea

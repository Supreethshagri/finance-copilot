from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.db import get_db
from models.user import User
from services.deps import get_current_user
from agents.sql_agent import run_sql_agent
from fastapi.responses import StreamingResponse
import io
from agents.report_agent import build_expense_report
from agents.supervisor import run_supervisor
from agents.analytics_agent import run_analytics_agent

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatQuery(BaseModel):
    question: str


@router.post("/sql")
def chat_sql(
    payload: ChatQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = run_sql_agent(payload.question, current_user.id, db)
    return result

@router.get("/report")
def download_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pdf_bytes = build_expense_report(current_user.id, db, current_user.email)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=expense_report.pdf"},
    )

@router.post("/ask")
def ask(
    payload: ChatQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Single endpoint — supervisor routes to the right agent."""
    return run_supervisor(payload.question, current_user.id, db)

@router.get("/insights")
def chat_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return run_analytics_agent(current_user.id, db)
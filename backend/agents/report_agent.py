import io
from collections import defaultdict
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)


def _gather(user_id: int, db: Session) -> dict:
    rows = db.execute(
        text("SELECT txn_date, description, amount, category "
             "FROM transactions WHERE user_id = :uid ORDER BY txn_date"),
        {"uid": user_id},
    ).fetchall()
    by_cat = defaultdict(float)
    total_spent = total_income = 0.0
    for r in rows:
        if r.amount < 0:
            by_cat[r.category or "Other"] += -r.amount
            total_spent += -r.amount
        else:
            total_income += r.amount
    return {"rows": rows, "by_cat": dict(by_cat),
            "total_spent": total_spent, "total_income": total_income}


def build_expense_report(user_id: int, db: Session, user_email: str) -> bytes:
    """Generate a monthly expense report PDF, returned as raw bytes."""
    data = _gather(user_id, db)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Expense Report", styles["Title"]))
    story.append(Paragraph(f"Account: {user_email}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Summary
    story.append(Paragraph("Summary", styles["Heading2"]))
    summary = [
        ["Total Income", f"INR {data['total_income']:.2f}"],
        ["Total Spent", f"INR {data['total_spent']:.2f}"],
        ["Net", f"INR {data['total_income'] - data['total_spent']:.2f}"],
    ]
    t = Table(summary, hAlign="LEFT", colWidths=[150, 150])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # By category
    if data["by_cat"]:
        story.append(Paragraph("Spending by Category", styles["Heading2"]))
        cat_rows = [["Category", "Amount (INR)"]]
        for cat, amt in sorted(data["by_cat"].items(), key=lambda x: -x[1]):
            cat_rows.append([cat, f"{amt:.2f}"])
        ct = Table(cat_rows, hAlign="LEFT", colWidths=[200, 150])
        ct.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]))
        story.append(ct)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
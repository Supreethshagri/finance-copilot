from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq

from config import settings

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=settings.GROQ_API_KEY,
    temperature=0.3,  # a little warmth for readable prose, but still grounded
)


def _compute_facts(user_id: int, db: Session) -> dict:
    """Deterministically compute spending facts in Python. No LLM here —
    these numbers must be exact."""
    rows = db.execute(
        text("SELECT txn_date, description, amount, category "
             "FROM transactions WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchall()

    if not rows:
        return {"empty": True}

    total_spent = sum(-r.amount for r in rows if r.amount < 0)
    total_income = sum(r.amount for r in rows if r.amount > 0)

    # spending grouped by day
    by_day = defaultdict(float)
    for r in rows:
        if r.amount < 0:
            by_day[str(r.txn_date)] += -r.amount
    biggest_day = max(by_day.items(), key=lambda x: x[1]) if by_day else (None, 0)

    # spending grouped by a simple keyword in description
    by_merchant = defaultdict(float)
    for r in rows:
        if r.amount < 0:
            key = r.description.split()[0] if r.description else "Other"
            by_merchant[key] += -r.amount
    top_merchant = max(by_merchant.items(), key=lambda x: x[1]) if by_merchant else (None, 0)

    return {
        "empty": False,
        "total_spent": round(total_spent, 2),
        "total_income": round(total_income, 2),
        "net": round(total_income - total_spent, 2),
        "biggest_day": {"date": biggest_day[0], "amount": round(biggest_day[1], 2)},
        "top_merchant": {"name": top_merchant[0], "amount": round(top_merchant[1], 2)},
        "transaction_count": len(rows),
    }


def run_analytics_agent(user_id: int, db: Session) -> dict:
    """Compute facts in Python, then let the LLM narrate them."""
    facts = _compute_facts(user_id, db)

    if facts["empty"]:
        return {"insights": "No transactions yet. Upload a statement to see insights.",
                "facts": facts}

    prompt = f"""You are a friendly personal finance assistant.
Based ONLY on these exact figures (all amounts in INR), write 3-4 short,
clear insight sentences for the user. Do not invent numbers not shown here.

Total spent: {facts['total_spent']}
Total income: {facts['total_income']}
Net (income - spent): {facts['net']}
Biggest spending day: {facts['biggest_day']['date']} ({facts['biggest_day']['amount']})
Top spending area: {facts['top_merchant']['name']} ({facts['top_merchant']['amount']})
Number of transactions: {facts['transaction_count']}
"""

    response = llm.invoke([
        {"role": "system", "content": "You give concise, accurate financial insights."},
        {"role": "user", "content": prompt},
    ])

    return {"insights": response.content.strip(), "facts": facts}
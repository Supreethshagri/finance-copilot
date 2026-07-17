from sqlalchemy import text
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq

from config import settings

CATEGORIES = ["Food", "Shopping", "Fuel", "Rent", "Entertainment",
              "Travel", "Bills", "Healthcare", "Income", "Other"]

# Fast path: keyword -> category. No LLM needed for these.
KEYWORD_MAP = {
    "swiggy": "Food", "zomato": "Food", "restaurant": "Food",
    "amazon": "Shopping", "flipkart": "Shopping", "myntra": "Shopping",
    "petrol": "Fuel", "hp": "Fuel", "indian oil": "Fuel", "fuel": "Fuel",
    "rent": "Rent",
    "netflix": "Entertainment", "spotify": "Entertainment", "bookmyshow": "Entertainment",
    "uber": "Travel", "ola": "Travel", "irctc": "Travel", "flight": "Travel",
    "electricity": "Bills", "recharge": "Bills", "bill": "Bills",
    "pharmacy": "Healthcare", "apollo": "Healthcare", "hospital": "Healthcare",
    "salary": "Income", "credit": "Income",
}

llm = ChatGroq(model="openai/gpt-oss-20b", api_key=settings.GROQ_API_KEY, temperature=0)


def _rule_categorize(description: str, amount: float) -> str | None:
    """Try keyword rules first. Returns None if no rule matches."""
    desc = description.lower()
    if amount > 0:
        return "Income"
    for keyword, cat in KEYWORD_MAP.items():
        if keyword in desc:
            return cat
    return None


def _llm_categorize(descriptions: list[str]) -> dict[str, str]:
    """Classify the leftovers in ONE batched LLM call (cheaper than one each)."""
    if not descriptions:
        return {}
    joined = "\n".join(f"- {d}" for d in descriptions)
    prompt = f"""Classify each transaction description into exactly one category
from this list: {', '.join(CATEGORIES)}.
Respond as 'description => Category', one per line, nothing else.

{joined}"""
    resp = llm.invoke([{"role": "user", "content": prompt}])
    mapping = {}
    for line in resp.content.strip().splitlines():
        if "=>" in line:
            d, c = line.split("=>", 1)
            cat = c.strip()
            mapping[d.strip().lstrip("- ").strip()] = cat if cat in CATEGORIES else "Other"
    return mapping


def run_expense_agent(user_id: int, db: Session) -> dict:
    """Categorize this user's uncategorized transactions and save results."""
    rows = db.execute(
        text("SELECT id, description, amount FROM transactions "
             "WHERE user_id = :uid AND category = 'Uncategorized'"),
        {"uid": user_id},
    ).fetchall()

    if not rows:
        return {"message": "No uncategorized transactions.", "updated": 0}

    updates = {}          # id -> category
    needs_llm = []        # descriptions the rules couldn't handle
    id_by_desc = {}

    for r in rows:
        cat = _rule_categorize(r.description, r.amount)
        if cat:
            updates[r.id] = cat
        else:
            needs_llm.append(r.description)
            id_by_desc.setdefault(r.description, []).append(r.id)

    llm_results = _llm_categorize(list(set(needs_llm)))
    for desc, cat in llm_results.items():
        for tid in id_by_desc.get(desc, []):
            updates[tid] = cat

    # write categories back, parameterized (no SQL injection)
    for tid, cat in updates.items():
        db.execute(
            text("UPDATE transactions SET category = :cat "
                 "WHERE id = :id AND user_id = :uid"),
            {"cat": cat, "id": tid, "uid": user_id},
        )
    db.commit()

    return {"message": f"Categorized {len(updates)} transactions.",
            "updated": len(updates)}
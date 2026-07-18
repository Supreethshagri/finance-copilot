import re
from sqlalchemy import text
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq

from config import settings

# The schema we let the model see. NOTE: only structure, never data.
SCHEMA_DESCRIPTION = """
Table: transactions
Columns:
  - id (integer)
  - user_id (integer)      -- owner of the row; ALWAYS filtered by the app
  - txn_date (date)
  - description (text)     -- e.g. 'Swiggy Order', 'Salary Credit'
  - amount (float)         -- negative = money spent, positive = money received
  - category (text)
"""

SYSTEM_PROMPT = f"""You are a SQL generator for a PostgreSQL database.
Given a user's question, output ONE single SQL SELECT statement and nothing else.

Rules:
- Output ONLY the SQL. No explanation, no markdown, no backticks.
- Only SELECT statements. Never INSERT/UPDATE/DELETE/DROP/ALTER.
- Query only the 'transactions' table.
- ALWAYS include the user_id filter given below in the WHERE clause.
- For spending questions, remember amount is negative for spends.
- Use ILIKE for text matching (case-insensitive).

{SCHEMA_DESCRIPTION}
"""

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=settings.GROQ_API_KEY,
    temperature=0,  # deterministic — we want the same SQL for the same question
)


def _clean_sql(raw: str) -> str:
    """Strip markdown fences / stray text the model might add."""
    raw = raw.strip()
    raw = re.sub(r"^```sql", "", raw, flags=re.IGNORECASE).strip()
    raw = raw.replace("```", "").strip()
    # take only up to the first semicolon (one statement)
    if ";" in raw:
        raw = raw.split(";")[0]
    return raw.strip()


def _is_safe_select(sql: str) -> bool:
    """Reject anything that isn't a single read-only SELECT."""
    lowered = sql.lower().strip()
    if not lowered.startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter",
                 "truncate", "grant", "revoke", ";", "--", "/*"]
    return not any(word in lowered for word in forbidden)


def _secure_scope(sql: str, user_id: int) -> str:
    """Wrap the model's query as a subquery and filter to this user's rows.
    This avoids fragile string-splicing into WHERE/ORDER BY/LIMIT clauses.
    Requires the inner query to expose user_id (enforced via the prompt)."""
    return (
        f"SELECT * FROM ({sql}) AS scoped WHERE scoped.user_id = {user_id}"
    )


def _columns_hint(sql: str) -> str:
    # crude check whether the select exposes user_id; if not, we can't wrap safely
    return sql.lower()


def _wrap_with_where(sql: str, user_id: int) -> str:
    """Fallback: inject WHERE user_id at the transactions table level."""
    # Safest approach: re-scope by requiring the model's SELECT to be against
    # transactions and appending an AND/WHERE on user_id.
    lowered = sql.lower()
    if " where " in lowered:
        return sql + f" AND user_id = {user_id}"
    # insert WHERE before GROUP BY / ORDER BY / LIMIT if present
    for kw in [" group by ", " order by ", " limit "]:
        idx = lowered.find(kw)
        if idx != -1:
            return sql[:idx] + f" WHERE user_id = {user_id} " + sql[idx:]
    return sql + f" WHERE user_id = {user_id}"


def run_sql_agent(question: str, user_id: int, db: Session) -> dict:
    """Convert a question to SQL, secure it, run it, return rows."""
    system = SYSTEM_PROMPT + f"""

CRITICAL: You MUST include this exact filter in every query's WHERE clause:
  user_id = {user_id}
For aggregates (SUM, COUNT, AVG), put it in the WHERE clause, not the SELECT list.
Example: SELECT SUM(amount) FROM transactions WHERE user_id = {user_id} AND description ILIKE '%swiggy%'
"""
    response = llm.invoke([
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ])
    sql = _clean_sql(response.content)

    if not _is_safe_select(sql):
        return {"error": "Generated query was not a safe read-only SELECT.", "sql": sql}

    # Verify the user filter is actually present — reject if the model omitted it.
    if f"user_id = {user_id}" not in sql.replace("user_id=", "user_id = "):
        return {"error": "Query rejected: missing required user scope.", "sql": sql}

    try:
        result = db.execute(text(sql))
        rows = [dict(r._mapping) for r in result]
    except Exception as e:
        return {"error": f"Query failed: {e}", "sql": sql}

    return {"sql": sql, "rows": rows, "row_count": len(rows)}
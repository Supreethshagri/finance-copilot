import pandas as pd
from datetime import datetime


# Map common bank-CSV column names to our fields. Real statements vary wildly;
# this keeps the messy input handling in ONE place.
DATE_COLS = ["date", "txn_date", "transaction date", "value date"]
DESC_COLS = ["description", "narration", "details", "particulars", "remarks"]
AMOUNT_COLS = ["amount", "amt", "transaction amount"]


def _find_col(columns, candidates):
    """Find the first matching column, case-insensitive."""
    lower = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def parse_csv(file_bytes: bytes) -> list[dict]:
    """Parse a bank-statement CSV into normalized transaction dicts.
    Raises ValueError with a clear message if required columns are missing."""
    from io import BytesIO
    df = pd.read_csv(BytesIO(file_bytes))

    date_col = _find_col(df.columns, DATE_COLS)
    desc_col = _find_col(df.columns, DESC_COLS)
    amount_col = _find_col(df.columns, AMOUNT_COLS)

    missing = []
    if not date_col:
        missing.append("date")
    if not desc_col:
        missing.append("description")
    if not amount_col:
        missing.append("amount")
    if missing:
        raise ValueError(
            f"CSV missing required column(s): {', '.join(missing)}. "
            f"Found columns: {list(df.columns)}"
        )

    rows = []
    for _, r in df.iterrows():
        try:
            txn_date = pd.to_datetime(r[date_col]).date()
            amount = float(r[amount_col])
        except (ValueError, TypeError):
            continue  # skip malformed rows rather than crashing the whole upload
        rows.append({
            "txn_date": txn_date,
            "description": str(r[desc_col]).strip(),
            "amount": amount,
        })
    return rows
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from models.user import User
from models.transaction import Transaction
from services.deps import get_current_user
from services.parser import parse_csv

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- route is protected
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    contents = await file.read()
    try:
        rows = parse_csv(contents)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not rows:
        raise HTTPException(status_code=422, detail="No valid rows found in file")

    # Every row is stamped with THIS user's id — that's the isolation.
    txns = [
        Transaction(
            user_id=current_user.id,
            txn_date=row["txn_date"],
            description=row["description"],
            amount=row["amount"],
        )
        for row in rows
    ]
    db.add_all(txns)
    db.commit()

    return {"inserted": len(txns), "message": f"Imported {len(txns)} transactions"}
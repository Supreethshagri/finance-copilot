import hashlib

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from models.user import User
from models.transaction import Transaction
from models.uploaded_file import UploadedFile
from services.deps import get_current_user
from services.parser import parse_csv

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    contents = await file.read()

    # Dedupe at the FILE level, not the transaction level. Identical
    # transactions are legitimate (two coffees on one day), but re-uploading
    # the same statement is almost always a mistake.
    file_hash = hashlib.sha256(contents).hexdigest()
    already = db.query(UploadedFile).filter(
        UploadedFile.user_id == current_user.id,
        UploadedFile.file_hash == file_hash,
    ).first()
    if already:
        raise HTTPException(
            status_code=409,
            detail=f"This file was already uploaded on "
                   f"{already.uploaded_at.strftime('%d %b %Y')}.",
        )

    try:
        rows = parse_csv(contents)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not rows:
        raise HTTPException(status_code=422, detail="No valid rows found in file")

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

    # Record the upload so the same file can't be imported again.
    db.add(UploadedFile(
        user_id=current_user.id,
        file_hash=file_hash,
        filename=file.filename,
        row_count=len(txns),
    ))
    db.commit()

    return {"inserted": len(txns),
            "message": f"Imported {len(txns)} transactions"}
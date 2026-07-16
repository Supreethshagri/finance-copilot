from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.sql import func

from database.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    # Links each row to its owner. index=True because we filter by it on
    # every single query. This column is what enforces data isolation.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    txn_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)          # negative = spend, positive = income
    category = Column(String, default="Uncategorized")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
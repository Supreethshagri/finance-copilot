from database.db import Base, engine
# Import every model so SQLAlchemy registers it before create_all runs.
from models.user import User  # noqa: F401
from models.transaction import Transaction  # noqa: F401

def init_db():
    """Creates all tables that don't exist yet. Safe to run repeatedly."""
    Base.metadata.create_all(bind=engine)
    print("Tables created (or already existed).")


if __name__ == "__main__":
    init_db()
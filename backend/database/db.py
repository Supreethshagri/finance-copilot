from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

# The engine is the actual connection pool to Postgres.
# pool_pre_ping checks a connection is alive before using it — important for
# Supabase, whose pooler drops idle connections. Without this you get random
# "server closed the connection" errors after the app sits idle.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# A session is one "conversation" with the DB for one request.
# autoflush/autocommit off = we control exactly when data is written.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Every model table will inherit from this Base.
Base = declarative_base()


def get_db():
    """FastAPI dependency: opens a DB session per request, always closes it.

    The try/finally guarantees the connection returns to the pool even if the
    request errors — otherwise you leak connections and eventually run out.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
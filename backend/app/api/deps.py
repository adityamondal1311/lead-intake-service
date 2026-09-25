from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


# One session per request, always closed. Transactions are opened and committed by services,
# not here, so each business operation decides its own boundary.
def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

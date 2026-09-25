from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal


# One session per request, always closed. Transactions are opened and committed by services,
# not here, so each business operation decides its own boundary.
def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]
# Injected rather than imported, so tests can override settings per test via dependency_overrides.
SettingsDep = Annotated[Settings, Depends(get_settings)]

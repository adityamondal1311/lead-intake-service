from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

# pool_pre_ping checks a pooled connection before use, so a Postgres restart or an idle
# connection dropped by the host does not surface as a failed request.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

# expire_on_commit=False keeps loaded objects readable after commit, so services can commit
# and then return the ORM objects for response serialization.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

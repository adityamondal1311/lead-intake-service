from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

# pool_pre_ping checks a pooled connection before use, so a Postgres restart or an idle
# connection dropped by the host does not surface as a failed request. connect_timeout bounds
# how long a request (including /health) can hang when the database is unreachable; psycopg's
# default is to wait indefinitely.
#
# hide_parameters keeps bound values out of SQLAlchemy exception messages. Without it, a failed
# INSERT logs its parameters (lead name, email, phone, the raw webhook payload) with the traceback.
engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
    hide_parameters=True,
)

# expire_on_commit=False keeps loaded objects readable after commit, so services can commit
# and then return the ORM objects for response serialization.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

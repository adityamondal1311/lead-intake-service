from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (registers every table on Base.metadata for autogenerate)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base

config = context.config

# Migration logs use the app's JSON logging (one object per line on stdout), so a deploy's log
# stream has one format from "applying migrations" through to serving requests. This replaces
# alembic.ini's plain-text logging config; unlike fileConfig, it never disables the app's
# existing loggers when migrations run in-process (the test suite).
configure_logging(get_settings().log_level)

# The URL comes from app settings (DATABASE_URL), so migrations and the app always target the
# same database. A URL set programmatically (e.g. by the test suite) takes precedence.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting (alembic upgrade head --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Off by default in Alembic: without it, changing a column default in a model would
            # not be detected by autogenerate or `alembic check` (the drift test).
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

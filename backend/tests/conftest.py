import os

# Point the app at the test database before any app module is imported: the engine in
# app.db.session is created at import time from DATABASE_URL. Env vars take precedence over
# backend/.env, so a developer's .env can never redirect tests at the dev database.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://lead_intake:lead_intake@localhost:5432/lead_intake_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Configure env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as db_session
from app.db.session import Base, get_db
from app.main import create_app


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(engine):
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    # Patch module-level engine/SessionLocal so app code uses the test engine
    db_session.engine = engine
    db_session.SessionLocal = TestingSession

    app = create_app()

    def override_get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

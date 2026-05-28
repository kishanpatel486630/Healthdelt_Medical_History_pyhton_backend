import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is on sys.path so `import app` works when pytest runs from elsewhere
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def temp_db_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("test_db")


@pytest.fixture(scope="function")
def client(temp_db_dir, monkeypatch):
    # Prepare a temporary sqlite file for tests
    db_file = temp_db_dir / "test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    # Patch runtime settings used by services/routes
    conf = importlib.import_module("app.config.settings")
    conf.settings.UPLOAD_DIR = str(temp_db_dir / "uploads")

    from app.database import Base, get_db
    from app.main import app as fastapi_app
    import app.api.routes.uploads as uploads_route

    # Fresh test engine/session per test for isolation
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Ensure upload route points to test upload directory
    uploads_route.BASE_UPLOAD_DIR = uploads_route.resolve_upload_root(conf.settings.UPLOAD_DIR)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as c:
        yield c

    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db_session_factory(client):
    """Expose the same SessionLocal used by the client fixture for direct DB seeding."""
    from app.database import get_db
    from app.main import app as fastapi_app

    override = fastapi_app.dependency_overrides[get_db]
    gen = override()
    session = next(gen)
    try:
        bind = session.get_bind()
    finally:
        session.close()

    return sessionmaker(autocommit=False, autoflush=False, bind=bind)

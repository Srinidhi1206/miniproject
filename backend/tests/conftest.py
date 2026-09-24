import os
import sys
import tempfile
from pathlib import Path

import pytest

# Isolated database + settings for the whole test session. Must run before app imports.
_tmp = Path(tempfile.mkdtemp(prefix="sentinel-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["LLM_PROVIDER"] = "none"
os.environ["URL_REPUTATION_API_KEY"] = ""
os.environ["SEED_DEMO"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def device():
    return {"X-Sentinel-Client": "pytest-device-0001"}

import os

import pytest


@pytest.fixture(scope="session")
def app_base_url() -> str:
    base_url = os.getenv("STLC_BASE_URL", "").strip()
    if not base_url:
        pytest.fail("Set STLC_BASE_URL to the application URL before running UI tests.")
    return base_url.rstrip("/")

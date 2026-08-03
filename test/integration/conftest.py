"""
Pytest configuration for integration tests.

Integration tests call the real Appcircle API. They are skipped when
APPCIRCLE_ACCESS_TOKEN is not set. Run with: pytest test/integration/ -v
"""

import os
import pytest


def pytest_configure(config):
    """Register the integration and integration_write markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires APPCIRCLE_ACCESS_TOKEN and real API)",
    )
    config.addinivalue_line(
        "markers",
        "integration_write: mark test as a write/action integration test (mutates real data; "
        "requires APPCIRCLE_ACCESS_TOKEN AND APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true)",
    )


@pytest.fixture(scope="module")
def integration_settings():
    """
    Provide settings configured from env for integration tests.
    Skips the test module if APPCIRCLE_ACCESS_TOKEN is not set.
    """
    token = os.getenv("APPCIRCLE_ACCESS_TOKEN")
    if not token:
        pytest.skip(
            "APPCIRCLE_ACCESS_TOKEN not set; skip with: pytest test/integration/ -v",
            allow_module_level=True,
        )
    from src.config.settings import settings

    api_url = os.getenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
    settings.configure(access_token=token, api_url=api_url)
    return settings


@pytest.fixture(scope="module")
def integration_write_settings(integration_settings):
    """
    Provide settings for write/action integration tests. In addition to
    APPCIRCLE_ACCESS_TOKEN (via integration_settings), requires the separate
    opt-in APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true so that running the plain
    integration suite (pytest test/integration/ -v) never triggers/cancels a
    real build or other write action against a live org by accident. Point
    APPCIRCLE_ACCESS_TOKEN at a dedicated test org before opting in.
    """
    if os.getenv("APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS", "").strip().lower() not in ("1", "true", "yes", "on"):
        pytest.skip(
            "APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS not set; write integration tests are opt-in. "
            "Set APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true (against a dedicated test org) to run them.",
            allow_module_level=True,
        )
    return integration_settings

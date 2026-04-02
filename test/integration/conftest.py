"""
Pytest configuration for integration tests.

Integration tests call the real Appcircle API. They are skipped when
APPCIRCLE_ACCESS_TOKEN is not set. Run with: pytest test/integration/ -v
"""

import os
import pytest


def pytest_configure(config):
    """Register the integration marker."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires APPCIRCLE_ACCESS_TOKEN and real API)",
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

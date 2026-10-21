"""
Shared pytest configuration and fixtures for Appcircle MCP server tests.

Provides:
- test_settings: Configure settings with a fake token so tools can run without real API credentials.
- mocked_api: respx mock router scoped to the Appcircle API base URL; use it to mock GET/POST/etc.
  and assert calls in unit tests without hitting the network.
"""

import pytest
import respx
from httpx import Response

# Ensure src is importable when running pytest from repo root (pythonpath is set in pyproject.toml)
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


# Default base URL used by ApiClient when settings are configured for tests
TEST_API_BASE_URL = "https://api.appcircle.io"
TEST_ACCESS_TOKEN = "test-token-for-unit-tests"


@pytest.fixture(autouse=True)
def test_settings(request):
    """
    Configure settings for tests so ApiClient and tools use a known base URL and token.
    Applied automatically to every test except those marked integration (they use real token).
    """
    if request.node.get_closest_marker("integration"):
        yield
        return
    from src.config.settings import settings

    settings.configure(access_token=TEST_ACCESS_TOKEN, api_url=TEST_API_BASE_URL)
    yield settings


@pytest.fixture
def mocked_api():
    """
    Shared respx mock for the Appcircle API. Use this in unit tests to mock HTTP
    responses without calling the real API.

    Example:
        def test_get_build_profiles(mocked_api):
            mocked_api.get("/build/v2/profiles").mock(
                return_value=Response(200, json=[{"id": "1", "name": "My Build", "buildPlatformType": 1}])
            )
            # ... call tool, assert response
    """
    with respx.mock(
        base_url=TEST_API_BASE_URL,
        assert_all_called=False,
        assert_all_mocked=False,
    ) as router:
        yield router


TEST_TOKEN_ISSUER = "https://auth.example.com/auth/realms/appcircle"
TEST_TOKEN_KID = "test-kid"


@pytest.fixture(scope="session")
def rsa_signing_key():
    """RSA private key that signs test tokens."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def token_signer(rsa_signing_key):
    """
    Return a helper that signs RS256 tokens shaped like Appcircle access tokens.

    Example:
        token = token_signer.sign()                  # valid token
        token = token_signer.sign(exp_offset=-60)    # expired
        token = token_signer.sign(issuer=None)       # no iss claim
    """
    import time

    import jwt

    class Signer:
        @staticmethod
        def sign(key=None, kid=TEST_TOKEN_KID, issuer=TEST_TOKEN_ISSUER, exp_offset=3600, **claims):
            payload = {"iss": issuer, "exp": int(time.time()) + exp_offset, "sub": "user-1", **claims}
            if issuer is None:
                payload.pop("iss")
            headers = {"kid": kid} if kid is not None else {}
            return jwt.encode(payload, key or rsa_signing_key, algorithm="RS256", headers=headers)

    return Signer


@pytest.fixture
def sample_build_profiles():
    """Sample build profiles list as returned by GET /build/v2/profiles."""
    return [
        {
            "id": "profile-uuid-1",
            "name": "iOS Production",
            "buildPlatformType": 1,
        },
        {
            "id": "profile-uuid-2",
            "name": "Android Debug",
            "buildPlatformType": 2,
        },
    ]


@pytest.fixture
def sample_report_response():
    """Sample report API response with data + pagination (e.g. GET /report/v2/sign)."""
    return {
        "data": [
            {
                "date": "2024-01-15",
                "buildProfileName": "iOS Prod",
                "organizationName": "Acme",
                "totalCount": 10,
                "successCount": 9,
                "failedCount": 1,
            }
        ],
        "pagination": {
            "page": 1,
            "perPage": 50,
            "totalCount": 1,
            "pageCount": 1,
            "enableNext": False,
        },
    }


@pytest.fixture
def sample_signing_report_response():
    """Sample signing report API response (GET /report/v1/sign)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 80,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "date": "2024-01-15",
                "buildProfileName": "iOS Prod",
                "organizationName": "Acme",
                "totalCount": 10,
                "successCount": 9,
                "failedCount": 1,
            }
        ],
    }


@pytest.fixture
def sample_build_history_response():
    """Sample build history API response (GET /report/v2/build)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 75,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "id": "aaaaaaaa000000000000000001",
                "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "organizationName": "Test Org",
                "buildId": "aaaaaaaa-0001-0000-0000-000000000001",
                "buildProfileName": "iOS Build",
                "branchName": "main",
                "buildDuration": 6.8,
                "buildStatus": 0,
                "buildStartDate": "2026-02-11T08:33:23Z",
                "artifactItems": [
                    {"filename": "app.ipa", "fileSize": 3.65, "resourceId": "mock-resource-id", "signed": False}
                ],
                "targetFile": {"filename": "app.ipa", "fileSize": 3.65, "resourceId": "mock-resource-id", "signed": False},
            }
        ],
    }


@pytest.fixture
def sample_distribution_app_version_report_response():
    """Sample distribution app version report API response (GET /report/v2/distribute-versions)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 60,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "date": "2024-01-20",
                "profileName": "Internal Testing",
                "organizationName": "Acme",
                "os": "ios",
                "versionCount": 5,
                "downloadCount": 42,
            }
        ],
    }


@pytest.fixture
def sample_distribution_sent_report_response():
    """Sample distribution sent report API response (GET /report/v2/distribute-sent)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 55,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "date": "2024-01-22",
                "profileName": "Internal Testing",
                "organizationName": "Acme",
                "os": "ios",
                "sentCount": 12,
                "recipientCount": 8,
            }
        ],
    }


@pytest.fixture
def sample_enterprise_app_store_app_usage_report_response():
    """Sample enterprise app store app usage API response (GET /store-report/v2/app-usage)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 45,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "date": "2024-01-18",
                "organizationName": "Acme",
                "storeProfileName": "Internal Store",
                "appUsageCount": 120,
                "uniqueUsers": 35,
            }
        ],
    }


@pytest.fixture
def sample_publish_status_report_response():
    """Sample publish status report API response (GET /report/v1/publish/status)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 70,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "id": "pub-uuid-1",
                "appName": "MyApp",
                "organizationName": "Acme",
                "status": 0,
                "publishDate": "2024-01-15T10:00:00Z",
                "platform": "ios",
            }
        ],
    }


@pytest.fixture
def sample_publish_resign_report_response():
    """Sample publish resign report API response (GET /report/v1/publish/resigns)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 55,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "id": "resign-uuid-1",
                "appName": "MyApp",
                "organizationName": "Acme",
                "status": 2,
                "resignDate": "2024-01-15T14:00:00Z",
                "platform": "ios",
            }
        ],
    }


@pytest.fixture
def sample_build_activity_log_response():
    """Sample build activity log API response (GET /report/v1/build/activity)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 60,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "profileId": "aaaaaaaa-0001-0000-0000-000000000001",
                "codePushAppId": None,
                "profileName": "iOS Build",
                "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "organizationName": "Acme",
                "rootOrganizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "userId": "aaaaaaaa-0002-0000-0000-000000000002",
                "userRole": "owner",
                "userEmail": "user@example.com",
                "platformType": 1,
                "action": 101,
                "description": "Workflow 'Default Push Workflow' updated for 'iOS Build' profile",
                "createDate": "2026-06-22T12:15:48.681421+00:00",
                "updateDate": "2026-06-22T12:15:48.6814215+00:00",
            }
        ],
        "summary": {"numberOfTransactions": 60},
    }


@pytest.fixture
def sample_signing_activity_log_response():
    """Sample signing activity log API response (GET /report/v2/sign/activity)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 70,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "profileId": "00000000-0000-0000-0000-000000000000",
                "keystoreProvId": "aaaaaaaa-0001-0000-0000-000000000001",
                "keystoreProvName": "iOS Distribution",
                "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "organizationName": "Acme",
                "rootOrganizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "userId": "00000000-0000-0000-0000-000000000000",
                "userRole": "N/A",
                "userEmail": "N/A",
                "platformType": "iOS",
                "action": 15,
                "description": "'iOS Distribution' provision will be expired in 1 Month",
                "createDate": "2026-06-22T13:36:21.7260341+00:00",
                "updateDate": "2026-06-22T13:36:21.7260339+00:00",
            }
        ],
    }


@pytest.fixture
def sample_publish_activity_log_response():
    """Sample publish activity log API response (GET /report/v2/publish/activity)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 65,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "profileId": "aaaaaaaa-0001-0000-0000-000000000001",
                "profileName": "HelloWorldApp",
                "publishFlowId": "00000000-0000-0000-0000-000000000000",
                "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "organizationName": "Acme",
                "rootOrganizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "userId": "aaaaaaaa-0002-0000-0000-000000000002",
                "userRole": "owner",
                "userEmail": "user@example.com",
                "platformType": "iOS",
                "action": 36,
                "description": "Re-sign process started for the app 'HelloWorldApp v:1.0.0'",
                "createDate": "2026-06-21T08:09:08.735138+00:00",
                "updateDate": "2026-06-21T08:09:08.7351379+00:00",
            }
        ],
    }


@pytest.fixture
def sample_build_queue_waiting_report_response():
    """Sample build queue waiting report API response (GET /report/v1/build/queue-waiting)."""
    return {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 2,
            "totalCount": 23,
            "enablePrevious": False,
            "enableNext": True,
        },
        "data": [
            {
                "id": "aaaaaaaa0001000000000001",
                "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "rootOrganizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "organizationName": "Acme",
                "userId": "aaaaaaaa-0002-0000-0000-000000000002",
                "initiatedBy": "user@example.com",
                "buildProfileName": "iOS Build",
                "branchName": "main",
                "commitId": "aaaaaaaa-0003-0000-0000-000000000003",
                "triggerType": 0,
                "os": 1,
                "machinePlan": 0,
                "xcodeVersion": "16.2.x",
                "runnerArchitecture": 1,
                "framework": 4,
                "buildDuration": 1.0,
                "buildStatus": 0,
                "buildStartDate": "2026-06-11T10:00:44.997Z",
                "buildFinishDate": "2026-06-11T10:00:55.995Z",
                "createDate": "2026-07-24T09:13:18.3140705+00:00",
                "updateDate": "2026-07-24T09:13:18.314071+00:00",
            }
        ],
        "summary": {"standard": 12.5, "velocity": 3.2, "ultra": 0.0},
    }

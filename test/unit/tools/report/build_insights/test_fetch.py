"""Unit tests for build-insights fetch helpers (respx-mocked)."""

import pytest
from httpx import Response

from src.core.api_client import ApiClient
from src.tools.report.build_insights.fetch import (
    fetch_all_build_history,
    fetch_all_build_profiles,
    fetch_all_queue_waiting,
    fetch_certificates,
    fetch_keystores,
    fetch_provisioning_profiles,
)


@pytest.mark.asyncio
class TestFetchAllBuildHistory:
    async def test_single_page_returns_data_as_is(self, mocked_api):
        body = {
            "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 2, "enablePrevious": False, "enableNext": False},
            "data": [{"id": "1"}, {"id": "2"}],
        }
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=body))

        async with ApiClient() as api_client:
            records = await fetch_all_build_history(api_client, start_date="2026-01-01", end_date="2026-01-31")

        assert records == [{"id": "1"}, {"id": "2"}]

    async def test_concatenates_all_pages(self, mocked_api):
        page1 = {
            "pagination": {"page": 1, "perPage": 100, "pageCount": 3, "totalCount": 250, "enablePrevious": False, "enableNext": True},
            "data": [{"id": str(i)} for i in range(100)],
        }
        page2 = {
            "pagination": {"page": 2, "perPage": 100, "pageCount": 3, "totalCount": 250, "enablePrevious": True, "enableNext": True},
            "data": [{"id": str(i)} for i in range(100, 200)],
        }
        page3 = {
            "pagination": {"page": 3, "perPage": 100, "pageCount": 3, "totalCount": 250, "enablePrevious": True, "enableNext": False},
            "data": [{"id": str(i)} for i in range(200, 250)],
        }
        pages_by_number = {"1": page1, "2": page2, "3": page3}

        def responder(request):
            page = request.url.params.get("page", "1")
            return Response(200, json=pages_by_number[page])

        mocked_api.get("/report/v2/build").mock(side_effect=responder)

        async with ApiClient() as api_client:
            records = await fetch_all_build_history(api_client, start_date="2026-01-01", end_date="2026-01-31")

        assert len(records) == 250
        assert {r["id"] for r in records} == {str(i) for i in range(250)}

    async def test_forwards_filters_as_query_params(self, mocked_api):
        body = {"pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 0}, "data": []}
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=body))

        async with ApiClient() as api_client:
            await fetch_all_build_history(api_client, start_date="2026-01-01", end_date="2026-01-31")

        params = mocked_api.calls.last.request.url.params
        assert params.get("startDate") == "2026-01-01"
        assert params.get("endDate") == "2026-01-31"
        assert params.get("size") == "100"


@pytest.mark.asyncio
class TestFetchAllQueueWaiting:
    async def test_single_page_returns_data_as_is(self, mocked_api):
        body = {
            "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 2, "enablePrevious": False, "enableNext": False},
            "data": [{"id": "1", "buildDuration": 1.0}, {"id": "2", "buildDuration": 2.0}],
            "summary": {"totalBuildsRun": 2, "totalBuildWaitingDuration": 3.0},
        }
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=body))

        async with ApiClient() as api_client:
            result = await fetch_all_queue_waiting(api_client, start_date="2026-01-01", end_date="2026-01-31")

        assert result["records"] == [{"id": "1", "buildDuration": 1.0}, {"id": "2", "buildDuration": 2.0}]

    async def test_captures_summary_including_plan_breakdown(self, mocked_api):
        body = {
            "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 1, "enablePrevious": False, "enableNext": False},
            "data": [{"id": "1", "buildDuration": 1.0}],
            "summary": {"totalBuildsRun": 1, "totalBuildWaitingDuration": 1.0, "standard": 0.0, "velocity": 1.0, "ultra": 0.0},
        }
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=body))

        async with ApiClient() as api_client:
            result = await fetch_all_queue_waiting(api_client, start_date="2026-01-01", end_date="2026-01-31")

        assert result["summary"] == {
            "totalBuildsRun": 1, "totalBuildWaitingDuration": 1.0, "standard": 0.0, "velocity": 1.0, "ultra": 0.0,
        }

    async def test_summary_absent_returns_none(self, mocked_api):
        body = {
            "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 0, "enablePrevious": False, "enableNext": False},
            "data": [],
        }
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=body))

        async with ApiClient() as api_client:
            result = await fetch_all_queue_waiting(api_client, start_date="2026-01-01", end_date="2026-01-31")

        assert result["summary"] is None

    async def test_concatenates_all_pages(self, mocked_api):
        page1 = {
            "pagination": {"page": 1, "perPage": 100, "pageCount": 2, "totalCount": 150, "enablePrevious": False, "enableNext": True},
            "data": [{"id": str(i)} for i in range(100)],
            "summary": {"standard": 0.0, "velocity": 150.0, "ultra": 0.0},
        }
        page2 = {
            "pagination": {"page": 2, "perPage": 100, "pageCount": 2, "totalCount": 150, "enablePrevious": True, "enableNext": False},
            "data": [{"id": str(i)} for i in range(100, 150)],
        }
        pages_by_number = {"1": page1, "2": page2}

        def responder(request):
            page = request.url.params.get("page", "1")
            return Response(200, json=pages_by_number[page])

        mocked_api.get("/report/v1/build/queue-waiting").mock(side_effect=responder)

        async with ApiClient() as api_client:
            result = await fetch_all_queue_waiting(api_client, start_date="2026-01-01", end_date="2026-01-31")

        assert len(result["records"]) == 150
        # Summary is taken from page 1 only -- it's the whole query's totals,
        # not a per-page partial sum.
        assert result["summary"] == {"standard": 0.0, "velocity": 150.0, "ultra": 0.0}

    async def test_forwards_filters_as_query_params(self, mocked_api):
        body = {"pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 0}, "data": []}
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=body))

        async with ApiClient() as api_client:
            await fetch_all_queue_waiting(api_client, start_date="2026-01-01", end_date="2026-01-31")

        params = mocked_api.calls.last.request.url.params
        assert params.get("startDate") == "2026-01-01"
        assert params.get("endDate") == "2026-01-31"
        assert params.get("size") == "100"


@pytest.mark.asyncio
class TestFetchAllBuildProfiles:
    async def test_returns_raw_list_response_as_is(self, mocked_api):
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(200, json=[{"id": "1", "name": "A"}, {"id": "2", "name": "B"}])
        )

        async with ApiClient() as api_client:
            profiles = await fetch_all_build_profiles(api_client)

        assert profiles == [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]

    async def test_normalizes_dict_wrapped_response(self, mocked_api):
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(200, json={"data": [{"id": "1", "name": "A"}]})
        )

        async with ApiClient() as api_client:
            profiles = await fetch_all_build_profiles(api_client)

        assert profiles == [{"id": "1", "name": "A"}]

    async def test_dict_response_with_no_recognized_key_returns_empty_list(self, mocked_api):
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json={"unexpected": "shape"}))

        async with ApiClient() as api_client:
            profiles = await fetch_all_build_profiles(api_client)

        assert profiles == []

    async def test_unrecognized_response_type_returns_empty_list(self, mocked_api):
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json="not a list or dict"))

        async with ApiClient() as api_client:
            profiles = await fetch_all_build_profiles(api_client)

        assert profiles == []

    async def test_single_call_no_pagination_params(self, mocked_api):
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[]))

        async with ApiClient() as api_client:
            await fetch_all_build_profiles(api_client)

        assert len(mocked_api.calls) == 1
        assert "page" not in mocked_api.calls.last.request.url.params

    async def test_returns_profiles_as_is_no_org_filter(self, mocked_api):
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(200, json=[
                {"id": "1", "name": "A", "organizationId": "org-1"},
                {"id": "2", "name": "B", "organizationId": "org-2"},
            ])
        )

        async with ApiClient() as api_client:
            profiles = await fetch_all_build_profiles(api_client)

        assert len(profiles) == 2


@pytest.mark.asyncio
class TestFetchCertificates:
    async def test_returns_raw_list_response_as_is(self, mocked_api):
        mocked_api.get("/signing-identity/v2/certificates").mock(
            return_value=Response(200, json=[{"id": "1", "name": "Cert A", "expireDate": "2025-12-31T08:43:29+00:00"}])
        )
        async with ApiClient() as api_client:
            certificates = await fetch_certificates(api_client)
        assert certificates == [{"id": "1", "name": "Cert A", "expireDate": "2025-12-31T08:43:29+00:00"}]

    async def test_normalizes_dict_wrapped_response(self, mocked_api):
        mocked_api.get("/signing-identity/v2/certificates").mock(
            return_value=Response(200, json={"data": [{"id": "1"}]})
        )
        async with ApiClient() as api_client:
            certificates = await fetch_certificates(api_client)
        assert certificates == [{"id": "1"}]

    async def test_unrecognized_response_returns_empty_list(self, mocked_api):
        mocked_api.get("/signing-identity/v2/certificates").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_certificates(api_client) == []


@pytest.mark.asyncio
class TestFetchProvisioningProfiles:
    async def test_returns_raw_list_response_as_is(self, mocked_api):
        mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(
            return_value=Response(200, json=[{"id": "1", "name": "Profile A"}])
        )
        async with ApiClient() as api_client:
            profiles = await fetch_provisioning_profiles(api_client)
        assert profiles == [{"id": "1", "name": "Profile A"}]

    async def test_unrecognized_response_returns_empty_list(self, mocked_api):
        mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_provisioning_profiles(api_client) == []


@pytest.mark.asyncio
class TestFetchKeystores:
    async def test_returns_raw_list_response_as_is(self, mocked_api):
        mocked_api.get("/signing-identity/v2/keystores").mock(
            return_value=Response(200, json=[{"id": "1", "name": "Keystore A"}])
        )
        async with ApiClient() as api_client:
            keystores = await fetch_keystores(api_client)
        assert keystores == [{"id": "1", "name": "Keystore A"}]

    async def test_unrecognized_response_returns_empty_list(self, mocked_api):
        mocked_api.get("/signing-identity/v2/keystores").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_keystores(api_client) == []

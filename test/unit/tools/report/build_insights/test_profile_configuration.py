"""Unit tests for build-insights profile-configuration fetch/resolve helpers
(respx-mocked)."""

import pytest
from httpx import Response

from src.core.api_client import ApiClient
from src.tools.report.build_insights.profile_configuration import (
    fetch_configuration_detail,
    fetch_configuration_list,
    fetch_profile_configuration,
    find_configuration_id,
    resolve_configuration_name,
)


def _build(profile="A", configuration="Default Configuration"):
    return {"buildProfileName": profile, "configurationName": configuration}


class TestResolveConfigurationName:
    def test_most_common_configuration_wins(self):
        curr_builds = [
            _build(configuration="Default Configuration"),
            _build(configuration="Default Configuration"),
            _build(configuration="Other Configuration"),
        ]
        assert resolve_configuration_name(curr_builds, "A") == "Default Configuration"

    def test_none_when_no_builds_for_profile(self):
        curr_builds = [_build(profile="B")]
        assert resolve_configuration_name(curr_builds, "A") is None

    def test_none_when_configuration_name_missing(self):
        curr_builds = [{"buildProfileName": "A"}]
        assert resolve_configuration_name(curr_builds, "A") is None

    def test_not_split_by_trigger_category(self):
        # Unlike resolve_push_pr_workflow_names, this resolves one overall
        # configuration regardless of triggerCategory.
        curr_builds = [
            {"buildProfileName": "A", "configurationName": "Cfg", "triggerCategory": 2},
            {"buildProfileName": "A", "configurationName": "Cfg", "triggerCategory": 1},
        ]
        assert resolve_configuration_name(curr_builds, "A") == "Cfg"


class TestFindConfigurationId:
    def test_finds_matching_configuration_id(self):
        configurations = [{"id": "1", "configurationName": "A"}, {"id": "2", "configurationName": "B"}]
        assert find_configuration_id(configurations, "B") == "2"

    def test_none_when_not_found(self):
        configurations = [{"id": "1", "configurationName": "A"}]
        assert find_configuration_id(configurations, "Missing") is None


@pytest.mark.asyncio
class TestFetchConfigurationList:
    async def test_flattens_item1_and_discards_item2(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/configurations").mock(
            return_value=Response(200, json=[
                {"item1": {"id": "1", "configurationName": "Default Configuration"}, "item2": []},
                {"item1": {"id": "2", "configurationName": "Other"}, "item2": []},
            ])
        )
        async with ApiClient() as api_client:
            configurations = await fetch_configuration_list(api_client, "p1")
        assert configurations == [
            {"id": "1", "configurationName": "Default Configuration"},
            {"id": "2", "configurationName": "Other"},
        ]

    async def test_unrecognized_response_returns_empty_list(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/configurations").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_configuration_list(api_client, "p1") == []

    async def test_entries_missing_item1_are_skipped(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/configurations").mock(
            return_value=Response(200, json=[{"item2": []}, {"item1": {"id": "1", "configurationName": "A"}, "item2": []}])
        )
        async with ApiClient() as api_client:
            configurations = await fetch_configuration_list(api_client, "p1")
        assert configurations == [{"id": "1", "configurationName": "A"}]


@pytest.mark.asyncio
class TestFetchConfigurationDetail:
    async def test_extracts_environment_variables_and_signing_identities(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/configurations/cfg-1").mock(
            return_value=Response(200, json={
                "environmentVariables": ["11111111-1111-1111-1111-111111111111"],
                "signingIdentities": [
                    {"signingIdentityType": 2, "entityId": "22222222-2222-2222-2222-222222222222", "bundleIdentifier": None},
                ],
            })
        )
        async with ApiClient() as api_client:
            detail = await fetch_configuration_detail(api_client, "p1", "cfg-1")
        assert detail == {
            "environment_variables": ["11111111-1111-1111-1111-111111111111"],
            "signing_identities": [
                {"signingIdentityType": 2, "entityId": "22222222-2222-2222-2222-222222222222", "bundleIdentifier": None},
            ],
        }

    async def test_missing_fields_default_to_empty_lists(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/configurations/cfg-1").mock(
            return_value=Response(200, json={"id": "cfg-1"})
        )
        async with ApiClient() as api_client:
            detail = await fetch_configuration_detail(api_client, "p1", "cfg-1")
        assert detail == {"environment_variables": [], "signing_identities": []}

    async def test_non_dict_response_returns_none(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/configurations/cfg-1").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_configuration_detail(api_client, "p1", "cfg-1") is None


@pytest.mark.asyncio
class TestFetchProfileConfiguration:
    async def test_returns_none_when_no_configuration_name_resolves(self, mocked_api):
        curr_builds = [{"buildProfileName": "A"}]  # no configurationName
        async with ApiClient() as api_client:
            result = await fetch_profile_configuration(api_client, curr_builds, "A", "p1")
        assert result is None
        assert len(mocked_api.calls) == 0  # no fetch attempted at all

    async def test_returns_none_when_configuration_name_unmatched(self, mocked_api):
        curr_builds = [_build(configuration="Missing Configuration")]
        mocked_api.get("/build/v2/profiles/p1/configurations").mock(
            return_value=Response(200, json=[{"item1": {"id": "1", "configurationName": "Other"}, "item2": []}])
        )
        async with ApiClient() as api_client:
            result = await fetch_profile_configuration(api_client, curr_builds, "A", "p1")
        assert result is None

    async def test_fetches_resolved_configuration_end_to_end(self, mocked_api):
        curr_builds = [_build(configuration="Default Configuration")]
        mocked_api.get("/build/v2/profiles/p1/configurations").mock(
            return_value=Response(200, json=[
                {"item1": {"id": "cfg-1", "configurationName": "Default Configuration"}, "item2": []},
            ])
        )
        mocked_api.get("/build/v2/profiles/p1/configurations/cfg-1").mock(
            return_value=Response(200, json={
                "environmentVariables": ["11111111-1111-1111-1111-111111111111"],
                "signingIdentities": [],
            })
        )
        async with ApiClient() as api_client:
            result = await fetch_profile_configuration(api_client, curr_builds, "A", "p1")
        assert result == {"environment_variables": ["11111111-1111-1111-1111-111111111111"], "signing_identities": []}

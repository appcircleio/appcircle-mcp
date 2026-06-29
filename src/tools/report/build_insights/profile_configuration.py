"""Fetch and resolve which build configuration is "the one used" by a
profile this period, for the build-insights report's Maturity Assessment
Security check.

A profile's push/PR/tag trigger rules can each carry a different
configurationId, so there's no single "the" configuration from trigger
config alone. Identity is instead resolved from build history: the
most-common `configurationName` among the profile's builds this period.
"""

from collections import Counter
from typing import Any, Dict, List, Optional

from ....core.api_client import ApiClient


def resolve_configuration_name(curr_builds: List[Dict[str, Any]], profile: str) -> Optional[str]:
    """Most-common `configurationName` among `profile`'s builds this period.
    `None` if the profile had no builds, or none carried a configurationName
    (e.g. an Appcircle role restriction stripping the field)."""
    names = Counter(
        build["configurationName"]
        for build in curr_builds
        if build["buildProfileName"] == profile and build.get("configurationName")
    )
    return names.most_common(1)[0][0] if names else None


async def fetch_configuration_list(api_client: ApiClient, profile_id: str) -> List[Dict[str, Any]]:
    """GET /build/v2/profiles/{profile_id}/configurations -- a bare list of
    {"item1": {id, configurationName, ...}, "item2": []}. `item2` is
    discarded, unrelated to this feature."""
    response = await api_client.get(f"/build/v2/profiles/{profile_id}/configurations")
    if not isinstance(response, list):
        return []
    return [entry["item1"] for entry in response if isinstance(entry, dict) and entry.get("item1")]


def find_configuration_id(configurations: List[Dict[str, Any]], configuration_name: str) -> Optional[str]:
    for configuration in configurations:
        if configuration.get("configurationName") == configuration_name:
            return configuration.get("id")
    return None


async def fetch_configuration_detail(
    api_client: ApiClient,
    profile_id: str,
    configuration_id: str,
) -> Optional[Dict[str, Any]]:
    """GET .../configurations/{configuration_id} -- carries
    `environmentVariables` (list of UUIDs) and `signingIdentities` (list of
    {signingIdentityType, entityId, bundleIdentifier})."""
    response = await api_client.get(f"/build/v2/profiles/{profile_id}/configurations/{configuration_id}")
    if not isinstance(response, dict):
        return None
    return {
        "environment_variables": response.get("environmentVariables") or [],
        "signing_identities": response.get("signingIdentities") or [],
    }


async def fetch_profile_configuration(
    api_client: ApiClient,
    curr_builds: List[Dict[str, Any]],
    profile: str,
    profile_id: str,
) -> Optional[Dict[str, Any]]:
    """Resolve and fetch the parsed configuration "used" by one profile this
    period. `None` if no configuration name resolves from build history, or
    it can't be matched to a configuration id.
    """
    configuration_name = resolve_configuration_name(curr_builds, profile)
    if not configuration_name:
        return None

    configurations = await fetch_configuration_list(api_client, profile_id)
    configuration_id = find_configuration_id(configurations, configuration_name)
    if not configuration_id:
        return None

    return await fetch_configuration_detail(api_client, profile_id, configuration_id)

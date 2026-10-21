"""Path-injection regression tests: every tool that interpolates an ID into an API path
rejects traversal/encoded/query payloads with a validation_error and sends no upstream request."""

import pytest

from src.tools.build_module.cancel_build import cancel_build
from src.tools.build_module.get_build_configuration_details import get_build_configuration_details
from src.tools.build_module.get_build_logs import get_build_logs
from src.tools.build_module.get_build_profile_details import get_build_profile_details
from src.tools.build_module.get_build_profile_workflows import get_build_profile_workflows
from src.tools.build_module.get_build_status import get_build_status
from src.tools.build_module.get_commit_details import get_commit_details
from src.tools.build_module.get_workflow_detail import get_workflow_detail
from src.tools.build_module.trigger_build import trigger_build
from src.tools.enterprise_app_store.get_store_profile_details import get_store_profile_details
from src.tools.publish_to_stores.get_app_version_metadata import get_app_version_metadata
from src.tools.publish_to_stores.get_intune_metadata import get_intune_metadata
from src.tools.publish_to_stores.get_metadata_locales import get_metadata_locales
from src.tools.publish_to_stores.get_publish_details import get_publish_details
from src.tools.publish_to_stores.get_publish_flows import get_publish_flows
from src.tools.publish_to_stores.get_publish_metadata_lock_status import get_publish_metadata_lock_status
from src.tools.publish_to_stores.get_publish_profile_details import get_publish_profile_details
from src.tools.publish_to_stores.get_publish_step_logs import get_publish_step_logs
from src.tools.publish_to_stores.start_publish import start_publish
from src.tools.publish_to_stores.stop_publish import stop_publish
from src.tools.testing_distribution.get_distribution_profile_details import get_distribution_profile_details
from src.tools.testing_distribution.send_app_version_to_testers import send_app_version_to_testers
from src.tools.testing_distribution.update_app_version_release_notes import update_app_version_release_notes

VALID_ID = "f4e4d8f9-ae28-4e82-a7bd-5e02338c2260"

PAYLOADS = [
    "../../../identity/v1/users",
    "..%2f..%2fidentity%2fv1%2fusers",
    "%2e%2e%2f%2e%2e%2fidentity",
    "other-id/configurations",
    "..\\..\\identity",
    "x?admin=true",
    "x#",
]

# (tool, valid kwargs, ID arguments that are interpolated into the path)
CASES = [
    (cancel_build, {"task_id": VALID_ID}, ["task_id"]),
    (get_build_configuration_details, {"profile_id": VALID_ID, "configuration_id": VALID_ID}, ["profile_id", "configuration_id"]),
    (get_build_logs, {"commit_id": VALID_ID, "build_id": VALID_ID}, ["commit_id", "build_id"]),
    (get_build_profile_details, {"profile_id": VALID_ID}, ["profile_id"]),
    (get_build_profile_workflows, {"profile_id": VALID_ID}, ["profile_id"]),
    (get_build_status, {"commit_id": VALID_ID, "build_id": VALID_ID}, ["commit_id", "build_id"]),
    (get_commit_details, {"commit_id": VALID_ID}, ["commit_id"]),
    (get_commit_details, {"commit_hash": "15d2bb0bac20cd8a564d4dbdf7bf2948321f7908"}, ["commit_hash"]),
    (get_workflow_detail, {"profile_id": VALID_ID, "workflow_id": VALID_ID}, ["profile_id", "workflow_id"]),
    (trigger_build, {"commit_id": VALID_ID}, ["commit_id"]),
    (trigger_build, {"profile_id": VALID_ID, "workflow_id": VALID_ID}, ["profile_id", "workflow_id"]),
    (get_store_profile_details, {"profile_id": VALID_ID}, ["profile_id"]),
    (get_app_version_metadata, {"platform_type": "ios", "profile_id": VALID_ID, "app_version_id": VALID_ID}, ["profile_id", "app_version_id"]),
    (get_intune_metadata, {"platform_type": "ios", "profile_id": VALID_ID, "app_version_id": VALID_ID}, ["profile_id", "app_version_id"]),
    (get_metadata_locales, {"platform_type": "ios", "profile_id": VALID_ID, "app_version_id": VALID_ID}, ["profile_id", "app_version_id"]),
    (get_publish_details, {"platform_type": "ios", "profile_id": VALID_ID, "app_version_id": VALID_ID}, ["profile_id", "app_version_id"]),
    (get_publish_flows, {"platform_type": "ios", "profile_id": VALID_ID}, ["profile_id"]),
    (get_publish_metadata_lock_status, {"platform_type": "ios", "profile_id": VALID_ID}, ["profile_id"]),
    (get_publish_profile_details, {"platform_type": "ios", "profile_id": VALID_ID}, ["profile_id"]),
    (get_publish_step_logs, {"platform_type": "ios", "profile_id": VALID_ID, "publish_id": VALID_ID, "step_id": VALID_ID}, ["profile_id", "publish_id", "step_id"]),
    (start_publish, {"platform_type": "ios", "profile_id": VALID_ID, "publish_id": VALID_ID}, ["profile_id", "publish_id"]),
    (stop_publish, {"platform_type": "ios", "profile_id": VALID_ID, "publish_id": VALID_ID}, ["profile_id", "publish_id"]),
    (get_distribution_profile_details, {"profile_id": VALID_ID}, ["profile_id"]),
    (send_app_version_to_testers, {"profile_id": VALID_ID, "app_version_id": VALID_ID, "message": "m", "testers": ["a@b.com"]}, ["profile_id", "app_version_id"]),
    (update_app_version_release_notes, {"profile_id": VALID_ID, "app_version_id": VALID_ID, "message": "m"}, ["profile_id", "app_version_id"]),
]

PARAMS = [
    pytest.param(tool, {**kwargs, arg: payload}, arg, id=f"{tool.__name__}-{arg}-{payload}")
    for tool, kwargs, args in CASES
    for arg in args
    for payload in PAYLOADS
]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool, kwargs, arg", PARAMS)
async def test_injected_id_is_rejected_without_upstream_request(mocked_api, tool, kwargs, arg):
    """Unsafe ID values return validation_error naming the argument and never reach the API."""
    result = await tool(**kwargs)

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert arg in result["error"]["details"]
    assert mocked_api.calls.call_count == 0

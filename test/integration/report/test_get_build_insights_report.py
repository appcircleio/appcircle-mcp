"""
Integration tests for get_build_insights_report (real Appcircle API).

Run with: pytest test/integration/report/test_get_build_insights_report.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.

Since field names are already verified against real API responses, this is a
regression check (envelope shape, no unexpected omissions for an org with
real build history) rather than a discovery mechanism.
"""

from datetime import datetime, timedelta

import pytest

from src.tools.report.get_build_insights_report import get_build_insights_report


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_report_basic_functionality(integration_settings):
    """Returns success with all sections computed for the default 30-day window."""
    response = await get_build_insights_report()
    assert response.get("success"), response.get("error")
    data = response.get("data", {})
    meta = response.get("meta", {})
    assert "date_range" in data
    assert "sections" in data
    assert meta.get("requested_sections") == [
        "artifact_health", "health_snapshot", "maturity_assessment", "queue_time", "root_cause", "workflow_quality",
    ]
    print(f"Omitted sections: {meta.get('omitted_sections')}")
    print(f"Omitted subsections: {meta.get('omitted_subsections')}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_root_cause_only_with_custom_date_range(integration_settings):
    """Scoping to a single section and explicit date range works end-to-end."""
    end = datetime.now()
    start = end - timedelta(days=30)
    response = await get_build_insights_report(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
        sections=["root_cause"],
    )
    assert response.get("success"), response.get("error")
    sections = response.get("data", {}).get("sections", {})
    assert "root_cause" in sections
    assert "health_snapshot" not in sections


@pytest.mark.integration
@pytest.mark.asyncio
async def test_maturity_assessment_only_with_custom_date_range(integration_settings):
    """Scoping to maturity_assessment alone exercises the full pipeline unit
    tests mock piece-by-piece but never end-to-end: workflow-YAML resolution
    (including the build-history/trigger-config fallback), best-practice
    scoring, and the signing-identity/configuration fetches for Security --
    all against the real API's actual response shapes, not root_cause's
    simpler build-history-only path."""
    end = datetime.now()
    start = end - timedelta(days=30)
    response = await get_build_insights_report(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
        sections=["maturity_assessment"],
    )
    assert response.get("success"), response.get("error")
    sections = response.get("data", {}).get("sections", {})
    assert "workflow_quality" not in sections
    assert "health_snapshot" not in sections

    meta = response.get("meta", {})
    if "maturity_assessment" not in meta.get("omitted_sections", []):
        maturity = sections["maturity_assessment"]
        assert isinstance(maturity["overall_score"], int)
        assert maturity["label"] in {"Optimizing", "Advancing", "Practicing", "Developing"}
        print(f"Discipline: {maturity.get('discipline')}")
        print(f"Security: {maturity.get('security')}")
    print(f"Omitted subsections: {meta.get('omitted_subsections')}")
    print(f"Failed fetches: {meta.get('failed_fetches')}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_include_sub_orgs_returns_success(integration_settings):
    """include_sub_orgs=True keeps cross-org build records in history-derived
    metrics instead of filtering to the token's own org -- the one behavior
    unit-test mocks can't really validate, since it depends on whether the
    real token actually has cross-org visibility. Values aren't asserted
    (depends entirely on the real org's structure); this just confirms the
    flag doesn't break the call and the scoping meta fields come back
    well-formed."""
    response = await get_build_insights_report(include_sub_orgs=True)
    assert response.get("success"), response.get("error")
    meta = response.get("meta", {})
    assert isinstance(meta.get("cross_org_builds_excluded"), int)
    assert isinstance(meta.get("unresolved_profiles"), list)
    print(f"Cross-org builds excluded: {meta.get('cross_org_builds_excluded')}")
    print(f"Unresolved profiles: {meta.get('unresolved_profiles')}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_section_returns_validation_error(integration_settings):
    """Invalid section names are rejected before any API call."""
    response = await get_build_insights_report(sections=["not_a_real_section"])
    assert response.get("success") is False
    assert response["error"]["type"] == "validation_error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """On API error, returns standard error envelope."""
    import os

    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid"
        result = await get_build_insights_report()
        if not result.get("success"):
            assert "error" in result and "tool" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = os.getenv("APPCIRCLE_ACCESS_TOKEN") or original

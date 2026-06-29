"""Fetch helpers for the build-insights report.

Both functions expect `api_client` to be used inside an
`async with ApiClient() as api_client:` session so repeated calls share one
underlying connection instead of paying a fresh TCP/TLS handshake per page.
"""

import asyncio
from typing import Any, Dict, List, Optional

from ....core.api_client import ApiClient


async def fetch_all_build_history(
    api_client: ApiClient,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch every page of GET /report/v2/build for the given filters.

    Page 1 is fetched first to read `pagination.pageCount`, then the
    remaining pages are fetched concurrently over the same `api_client`.
    """
    params: Dict[str, Any] = {"page": "1", "size": str(page_size)}
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date

    first = await api_client.get("/report/v2/build", params=params)
    records: List[Dict[str, Any]] = list(first.get("data", []))
    total_pages = first.get("pagination", {}).get("pageCount", 1)

    if total_pages > 1:
        pages = await asyncio.gather(*[
            api_client.get("/report/v2/build", params={**params, "page": str(page)})
            for page in range(2, total_pages + 1)
        ])
        for page_response in pages:
            records.extend(page_response.get("data", []))

    return records


async def fetch_all_queue_waiting(
    api_client: ApiClient,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """Fetch every page of GET /report/v1/build/queue-waiting for the given filters.

    Same pagination shape as /report/v2/build (page 1 first to read
    `pagination.pageCount`, then the rest concurrently). Note: on *this*
    endpoint, `buildDuration` means queue wait time in minutes, not
    execution time, unlike on /report/v2/build.

    Returns `{"records": [...], "summary": {...} | None}`. `summary` is the
    org-wide totals object the API attaches to the response, including a
    standard/velocity/ultra machine-plan wait breakdown with no per-record
    equivalent. Taken from page 1 only, since it describes the whole
    filtered query rather than that one page.
    """
    params: Dict[str, Any] = {"page": "1", "size": str(page_size)}
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date

    first = await api_client.get("/report/v1/build/queue-waiting", params=params)
    records: List[Dict[str, Any]] = list(first.get("data", []))
    summary = first.get("summary")
    total_pages = first.get("pagination", {}).get("pageCount", 1)

    if total_pages > 1:
        pages = await asyncio.gather(*[
            api_client.get("/report/v1/build/queue-waiting", params={**params, "page": str(page)})
            for page in range(2, total_pages + 1)
        ])
        for page_response in pages:
            records.extend(page_response.get("data", []))

    return {"records": records, "summary": summary}


async def fetch_all_build_profiles(api_client: ApiClient) -> List[Dict[str, Any]]:
    """Fetch the full build profiles list.

    GET /build/v2/profiles ignores page/size and returns everything in one
    call as a bare JSON array, so this is a single request, not a
    pagination loop. Response shape is still normalized defensively (raw
    list vs. a dict wrapper), mirroring `get_build_profiles.py`.

    Always scoped to the calling token's own organization -- there is no
    server-side or client-side organization filter on this endpoint.
    """
    response = await api_client.get("/build/v2/profiles")

    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        raw = response.get("data") or response.get("items") or response.get("profiles") or []
        return raw if isinstance(raw, list) else []
    return []


def _normalize_list_response(response: Any) -> List[Dict[str, Any]]:
    """Shared normalization for the three signing-identity list endpoints
    below -- each is a bare unpaginated list, normalized defensively."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        items = response.get("data") or response.get("items") or []
        return items if isinstance(items, list) else []
    return []


async def fetch_certificates(api_client: ApiClient) -> List[Dict[str, Any]]:
    """GET /signing-identity/v2/certificates -- org-wide, single call, used
    by maturity_assessment's Security signing-expiry check."""
    response = await api_client.get("/signing-identity/v2/certificates")
    return _normalize_list_response(response)


async def fetch_provisioning_profiles(api_client: ApiClient) -> List[Dict[str, Any]]:
    """GET /signing-identity/v2/provisioning-profiles -- org-wide, single call."""
    response = await api_client.get("/signing-identity/v2/provisioning-profiles")
    return _normalize_list_response(response)


async def fetch_keystores(api_client: ApiClient) -> List[Dict[str, Any]]:
    """GET /signing-identity/v2/keystores -- org-wide, single call."""
    response = await api_client.get("/signing-identity/v2/keystores")
    return _normalize_list_response(response)

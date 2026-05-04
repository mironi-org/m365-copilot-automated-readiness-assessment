"""A365 Graph client helpers for per-package detail collection.

Uses the access token obtained during catalog fetch (_access_token key) to
retrieve per-package detail from /beta/copilot/admin/catalog/packages/{id} via
async httpx — avoiding a second interactive auth prompt.

Configurable env vars:
  A365_DETAIL_LIMIT       Maximum packages to fetch details for (default 500).
  A365_DETAIL_CONCURRENCY Maximum simultaneous in-flight requests (default 10).
"""

import asyncio
import os
import sys

import httpx

from Core.spinner import _stdout_lock, get_timestamp

_DETAIL_BASE_URL = "https://graph.microsoft.com/beta/copilot/admin/catalog/packages/{}"

# Fields kept from each detail response; longDescription excluded (too large).
_DETAIL_FIELDS = frozenset({
    "categories",
    "id",
    "displayName",
    "type",
    "shortDescription",
    "isBlocked",
    "supportedHosts",
    "lastModifiedDateTime",
    "publisher",
    "availableTo",
    "deployedTo",
    "elementTypes",
    "platform",
    "appId",
    "assetId",
    "version",
    "manifestVersion",
    "manifestId",
    "allowedUsersAndGroups",
    "acquireUsersAndGroups",
    "elementDetails",
})


async def get_a365_details(
    access_token,
    package_ids,
    progress_callback=None,
    silent=False,
    api_total_agents=None,
):
    """Async-fetch per-package detail for a list of IDs using the catalog access token.

    Args:
        access_token: Bearer token from the catalog payload (_access_token key).
        package_ids: Iterable of package ID strings from the catalog.
        progress_callback: Optional callable(done, total) for progress bar updates.
        silent: Suppress console status messages.
        api_total_agents: Optional total count returned by list API.

    Returns:
        list[dict]: Filtered detail dicts (fields in _DETAIL_FIELDS only).
                    Returns an empty list when the token is unavailable.
    """
    if not access_token or not package_ids:
        if not silent:
            with _stdout_lock:
                print(
                    f"[{get_timestamp()}] [INFO] A365 package detail fetch skipped "
                    "(no access token or package IDs)."
                )
        return []

    try:
        detail_limit = int(os.getenv("A365_DETAIL_LIMIT", "1000") or "1000")
    except Exception:
        detail_limit = 1000
    detail_limit = max(1, detail_limit)

    try:
        concurrency = int(os.getenv("A365_DETAIL_CONCURRENCY", "10") or "10")
    except Exception:
        concurrency = 10
    concurrency = max(1, min(30, concurrency))

    ids = [pid for pid in package_ids if pid][:detail_limit]
    total = len(ids)
    if not ids:
        return []

    if not silent:
        with _stdout_lock:
            print(
                f"[{get_timestamp()}] [INFO] A365 fetching package details: "
                f"{total} packages (concurrency={concurrency}, limit={detail_limit})..."
            )

    if progress_callback:
        progress_callback(0, total)

    sem = asyncio.Semaphore(concurrency)
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    done_count = 0
    error_count = 0
    skipped_count = 0   # 424 = package dependency not met in this tenant (expected)
    error_details = {}  # Track error summary by status code/type

    async def fetch_one(pkg_id, client):
        nonlocal done_count, error_count, skipped_count, error_details
        async with sem:
            url = _DETAIL_BASE_URL.format(pkg_id)
            try:
                r = await client.get(url, headers=auth_headers)
                if r.status_code == 200:
                    data = r.json()
                    filtered = {k: v for k, v in data.items() if k in _DETAIL_FIELDS}
                    done_count += 1
                    if progress_callback:
                        progress_callback(done_count, total)
                    return filtered
                if r.status_code == 424:
                    # Failed Dependency — package exists in global catalog but its
                    # underlying app/license dependency is not available in this tenant.
                    # This is expected for cross-tenant catalogs; don't count as an error.
                    skipped_count += 1
                    done_count += 1
                    if progress_callback:
                        progress_callback(done_count, total)
                    return None
                if r.status_code == 429:
                    # Single back-off retry on rate limit.
                    await asyncio.sleep(2.0)
                    r2 = await client.get(url, headers=auth_headers)
                    if r2.status_code == 200:
                        data = r2.json()
                        filtered = {k: v for k, v in data.items() if k in _DETAIL_FIELDS}
                        done_count += 1
                        if progress_callback:
                            progress_callback(done_count, total)
                        return filtered
                    if r2.status_code == 424:
                        skipped_count += 1
                        done_count += 1
                        if progress_callback:
                            progress_callback(done_count, total)
                        return None
                    # Failed after retry
                    status_key = f"HTTP {r2.status_code}"
                    error_details[status_key] = error_details.get(status_key, 0) + 1
                    error_count += 1
                else:
                    # Non-200 status
                    status_key = f"HTTP {r.status_code}"
                    error_details[status_key] = error_details.get(status_key, 0) + 1
                    error_count += 1
            except Exception as ex:
                error_type = type(ex).__name__
                error_details[error_type] = error_details.get(error_type, 0) + 1
                error_count += 1
            done_count += 1
            if progress_callback:
                progress_callback(done_count, total)
            return None

    async with httpx.AsyncClient(timeout=20.0) as client:
        raw = await asyncio.gather(*[fetch_one(pid, client) for pid in ids])

    results = [r for r in raw if isinstance(r, dict)]

    summary_total = total
    if isinstance(api_total_agents, int) and api_total_agents >= len(results):
        summary_total = api_total_agents

    with _stdout_lock:
        if error_count:
            error_breakdown = ", ".join(
                f"{count} {label}"
                for label, count in sorted(error_details.items(), key=lambda x: -x[1])
            )
            print(
                f"[{get_timestamp()}] [INFO] A365 detail fetch complete: API has full metadata for "
                f"{len(results)} Agents out of {summary_total} Agents and not for remaining {summary_total - len(results)} Agents "
                f"(non-metadata failures: {error_count}; {error_breakdown})."
            )
        else:
            print(
                f"[{get_timestamp()}] [INFO] A365 detail fetch complete: API has full metadata for "
                f"{len(results)} Agents out of {summary_total} Agents and not for remaining {summary_total - len(results)} Agents."
            )

    return results

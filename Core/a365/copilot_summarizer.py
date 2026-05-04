"""Optional GitHub Copilot API summarization helpers for A365 package rows."""

import json
import os
import random
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from Core.spinner import _stdout_lock, get_timestamp


DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_API_URL = "https://models.inference.ai.azure.com/chat/completions"
MAX_RETRIES = 3
DEFAULT_MAX_CALLS = 120

# Curated, verified Agent 365 doc URLs. AI link selection must stay within this allowlist.
AGENT365_DOC_ALLOWLIST = {
    "Overview": "https://learn.microsoft.com/en-us/microsoft-agent-365/overview",
    "Admin Overview": "https://learn.microsoft.com/en-us/microsoft-agent-365/",
    "Developer Overview": "https://learn.microsoft.com/en-us/microsoft-agent-365/developer/",
    "Developer Registration": "https://learn.microsoft.com/en-us/microsoft-agent-365/developer/registration",
    "Tooling Servers": "https://learn.microsoft.com/en-us/microsoft-agent-365/tooling-servers-overview",
    "Responsible AI": "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/responsible-ai-overview",
    "Entra": "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/capabilities-entra",
    "Governance": "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/capabilities-entra#agent-governance-and-lifecycles",
    "Observability": "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/capabilities-entra#register-and-manage-agents",
    "Security": "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/capabilities-entra#protect-agent-access-to-resources",
    # No dedicated Agent 365 Defender/Purview pages were discovered; map to closest verified pages.
    "Defender": "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/capabilities-entra#protect-agent-access-to-resources",
    "Purview": "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/responsible-ai-overview",
}


_state_lock = threading.Lock()
_cached_token = None
_cached_source = None
_api_disabled = False
_api_failure_announced = False
_next_allowed_time = 0.0
_cooldown_announced = False
_consecutive_429 = 0
_summaries_requested = 0
_summary_cache = {}


def _get_env_token():
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_MODELS_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            return value, key
    return "", ""


def _get_gh_cli_token():
    """Best-effort token discovery from GitHub CLI auth context."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip(), "gh auth token"
    except Exception:
        pass
    return "", ""


def _get_token_cached():
    global _cached_token, _cached_source

    with _state_lock:
        if _cached_token is not None:
            return _cached_token, _cached_source

    token, source = _get_env_token()
    if not token:
        token, source = _get_gh_cli_token()

    with _state_lock:
        _cached_token = token
        _cached_source = source

    return token, source


def get_runtime_mode():
    """Return summarization mode details for console messaging."""
    token, source = _get_token_cached()
    if token:
        return {
            "enabled": True,
            "source": source,
            "model": DEFAULT_MODEL,
            "endpoint": DEFAULT_API_URL,
        }
    return {
        "enabled": False,
        "reason": "No GitHub token found in env or GitHub CLI auth context",
    }


def _extract_text(response_json):
    try:
        return response_json["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def choose_agent365_doc_url(feature, observation, default_url=None):
    """Select the best Agent 365 doc URL from the verified allowlist.

    Always returns a URL present in AGENT365_DOC_ALLOWLIST.
    """
    fallback = default_url or AGENT365_DOC_ALLOWLIST["Overview"]
    if fallback not in AGENT365_DOC_ALLOWLIST.values():
        fallback = AGENT365_DOC_ALLOWLIST["Overview"]

    token, _ = _get_token_cached()
    if not token:
        return fallback

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    allowlist_rows = [
        {"topic": topic, "url": url}
        for topic, url in AGENT365_DOC_ALLOWLIST.items()
    ]

    request_body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You select the single best documentation URL for an A365 recommendation. "
                    "Choose only from the provided allowlist. "
                    "Return JSON only: {\"url\":\"<exact-allowlisted-url>\"}."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Feature: " + str(feature) + "\n"
                    + "Observation: " + str(observation) + "\n"
                    + "Allowlist:\n"
                    + json.dumps(allowlist_rows, ensure_ascii=True)
                    + "\nPick the single best URL."
                ),
            },
        ],
        "temperature": 0.0,
        "max_tokens": 120,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            for attempt in range(MAX_RETRIES):
                response = client.post(DEFAULT_API_URL, json=request_body, headers=auth_headers)
                if response.status_code < 400:
                    text = _extract_text(response.json())
                    json_text = _extract_json_block(text)
                    try:
                        parsed = json.loads(json_text or "{}")
                        url = str(parsed.get("url") or "").strip()
                        if url in AGENT365_DOC_ALLOWLIST.values():
                            return url
                    except Exception:
                        pass
                    return fallback
                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < MAX_RETRIES - 1:
                        retry_after = _parse_retry_after(response.headers)
                        wait = retry_after if retry_after is not None else (1.0 * (attempt + 1)) + random.uniform(0.0, 0.5)
                        time.sleep(max(0.5, min(wait, 8.0)))
                        continue
                break
    except Exception:
        pass

    return fallback


def _parse_retry_after(headers):
    """Return retry delay in seconds from Retry-After header when possible."""
    raw = (headers or {}).get("Retry-After")
    if not raw:
        return None

    try:
        seconds = float(str(raw).strip())
        if seconds >= 0:
            return seconds
    except Exception:
        pass

    try:
        dt = parsedate_to_datetime(str(raw).strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (dt - now).total_seconds())
    except Exception:
        return None


def _cache_key(package_row):
    if not isinstance(package_row, dict):
        return None

    package_id = str(package_row.get("id") or package_row.get("packageId") or "").strip()
    package_name = str(package_row.get("displayName") or package_row.get("name") or "").strip()
    package_status = str(package_row.get("status") or "").strip()

    if not package_id and not package_name:
        return None
    return f"{package_id}|{package_name}|{package_status}"


def _normalize_package_input(package_row):
    safe_payload = package_row if isinstance(package_row, dict) else {}
    return {
        "packageName": safe_payload.get("displayName") or safe_payload.get("name") or safe_payload.get("title") or "Unknown",
        "packageId": safe_payload.get("id") or safe_payload.get("packageId") or "Unknown",
        "typeOrCategory": safe_payload.get("type") or safe_payload.get("category") or "Unspecified",
        "status": safe_payload.get("status") or "Unknown",
        "publisher": safe_payload.get("publisher") or "Unknown",
        "tags": safe_payload.get("tags") if isinstance(safe_payload.get("tags"), list) else safe_payload.get("tags") or [],
        "purpose": safe_payload.get("description") or safe_payload.get("shortDescription") or safe_payload.get("summary") or "Unknown",
        "createdOrPublished": safe_payload.get("createdDateTime") or safe_payload.get("createdAt") or safe_payload.get("publishedDateTime") or safe_payload.get("lastModifiedDateTime") or "Unknown",
        "platform": safe_payload.get("platform") or safe_payload.get("platforms") or safe_payload.get("runtime") or safe_payload.get("supportedClients") or safe_payload.get("supportedPlatforms") or safe_payload.get("hostProducts") or [],
    }


def _extract_json_block(text):
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\\s*", "", stripped)
        stripped = re.sub(r"\\s*```$", "", stripped)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start:end + 1]
    return stripped


def _request_bulk_chunk(client, headers, chunk_payload):
    request_body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You summarize Microsoft 365 Copilot catalog package metadata for readiness reports. "
                    "Return JSON only in the format {\"summaries\":[{\"index\":<int>,\"summary\":<string>}]} with one entry per input row. "
                    "Each summary must be exactly 4 short lines:\n"
                    "1) Package: ...\n"
                    "2) Purpose/capability: ...\n"
                    "3) Lifecycle/platform: ...\n"
                    "4) Status/risk signal: ...\n"
                    "Do not include markdown or explanations outside JSON."
                ),
            },
            {
                "role": "user",
                "content": "Summarize these package rows:\n" + json.dumps({"rows": chunk_payload}, ensure_ascii=True),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }

    for attempt in range(MAX_RETRIES):
        response = client.post(DEFAULT_API_URL, json=request_body, headers=headers)

        if response.status_code < 400:
            text = _extract_text(response.json())
            json_text = _extract_json_block(text)
            try:
                parsed = json.loads(json_text or "{}")
                rows = parsed.get("summaries")
                if isinstance(rows, list):
                    return {"ok": True, "rows": rows}
            except Exception:
                pass
            return {"ok": True, "rows": []}

        if response.status_code == 429 or 500 <= response.status_code <= 599:
            if attempt < (MAX_RETRIES - 1):
                retry_after = _parse_retry_after(response.headers)
                if retry_after is not None:
                    wait_seconds = retry_after
                else:
                    wait_seconds = (1.5 * (attempt + 1)) + random.uniform(0.0, 0.8)
                time.sleep(max(0.5, min(wait_seconds, 8.0)))
                continue

        return {"ok": False, "status_code": response.status_code, "headers": dict(response.headers)}

    return {"ok": False, "status_code": 500, "headers": {}}


def summarize_package_rows_bulk(package_rows, chunk_size=25, progress_callback=None):
    """Bulk summarize package rows in chunks; returns {row_index: summary_text}."""
    global _api_disabled, _api_failure_announced, _next_allowed_time
    global _cooldown_announced, _consecutive_429, _summaries_requested

    if _api_disabled:
        return {}

    token, _ = _get_token_cached()
    if not token:
        return {}

    rows = package_rows if isinstance(package_rows, list) else []
    if not rows:
        return {}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        max_calls = int(os.getenv("A365_SUMMARY_MAX_CALLS", str(DEFAULT_MAX_CALLS)) or DEFAULT_MAX_CALLS)
    except Exception:
        max_calls = DEFAULT_MAX_CALLS

    size = max(5, min(100, int(chunk_size or 25)))
    results = {}
    total_chunks = (len(rows) + size - 1) // size
    completed_chunks = 0

    if callable(progress_callback):
        try:
            progress_callback(0, total_chunks)
        except Exception:
            pass

    with httpx.Client(timeout=45.0) as client:
        for start in range(0, len(rows), size):
            now = time.monotonic()
            with _state_lock:
                blocked_until = _next_allowed_time
                should_announce_cooldown = not _cooldown_announced
                exhausted = _summaries_requested >= max_calls

            if exhausted:
                break

            if now < blocked_until:
                if should_announce_cooldown:
                    remaining = max(0.0, blocked_until - now)
                    with _stdout_lock:
                        print(
                            f"\n[{get_timestamp()}] [WARN] A365 Copilot bulk summarization cooling down for {remaining:.1f}s; using fallback summaries for this window."
                        )
                    with _state_lock:
                        _cooldown_announced = True
                continue

            chunk = rows[start:start + size]
            chunk_payload = []
            for offset, package_row in enumerate(chunk):
                absolute_index = start + offset
                normalized = _normalize_package_input(package_row)
                normalized["index"] = absolute_index
                chunk_payload.append(normalized)

            with _state_lock:
                _summaries_requested += 1

            result = _request_bulk_chunk(client, headers, chunk_payload)
            if result.get("ok"):
                for item in result.get("rows", []):
                    try:
                        idx = int(item.get("index"))
                    except Exception:
                        continue
                    summary = str(item.get("summary") or "").strip()
                    if not summary:
                        continue
                    results[idx] = summary

                    if 0 <= idx < len(rows):
                        key = _cache_key(rows[idx])
                        if key:
                            with _state_lock:
                                _summary_cache[key] = summary

                with _state_lock:
                    _consecutive_429 = 0
                    _next_allowed_time = 0.0
                    _cooldown_announced = False
                    _api_failure_announced = False

                completed_chunks += 1
                if callable(progress_callback):
                    try:
                        progress_callback(completed_chunks, total_chunks)
                    except Exception:
                        pass
                continue

            status_code = int(result.get("status_code") or 0)
            headers_map = result.get("headers") or {}
            if status_code == 429:
                retry_after = _parse_retry_after(headers_map)
                with _state_lock:
                    _consecutive_429 += 1
                    _cooldown_announced = False
                    cooldown = retry_after
                    if cooldown is None:
                        cooldown = min(20.0, 2.0 * (2 ** min(_consecutive_429 - 1, 3))) + random.uniform(0.0, 1.0)
                    _next_allowed_time = time.monotonic() + max(1.0, cooldown)
                    should_announce = not _api_failure_announced
                    _api_failure_announced = True
                if should_announce:
                    with _stdout_lock:
                        print(
                            f"\n[{get_timestamp()}] [WARN] A365 Copilot bulk summarization is being rate limited (HTTP 429); using fallback summaries until cooldown ends."
                        )

                completed_chunks += 1
                if callable(progress_callback):
                    try:
                        progress_callback(completed_chunks, total_chunks)
                    except Exception:
                        pass
                continue

            with _state_lock:
                _api_disabled = True
                should_announce = not _api_failure_announced
                _api_failure_announced = True
            if should_announce:
                with _stdout_lock:
                    print(
                        f"\n[{get_timestamp()}] [WARN] A365 Copilot bulk summarization disabled after API HTTP {status_code}; using fallback summaries."
                    )

            completed_chunks += 1
            if callable(progress_callback):
                try:
                    progress_callback(completed_chunks, total_chunks)
                except Exception:
                    pass
            break

    return results


def summarize_package_row(package_row):
    """Return a 2-3 line summary for a package row using GitHub Copilot API.

    Uses implicit token discovery from environment variables or GitHub CLI auth.
    """
    global _api_disabled, _api_failure_announced, _next_allowed_time
    global _cooldown_announced, _consecutive_429, _summaries_requested

    if _api_disabled:
        return None

    token, _ = _get_token_cached()
    if not token:
        return None

    key = _cache_key(package_row)
    if key:
        with _state_lock:
            cached = _summary_cache.get(key)
        if cached:
            return cached

    now = time.monotonic()
    with _state_lock:
        blocked_until = _next_allowed_time
        should_announce_cooldown = not _cooldown_announced

    if now < blocked_until:
        if should_announce_cooldown:
            remaining = max(0.0, blocked_until - now)
            with _stdout_lock:
                print(
                    f"\n[{get_timestamp()}] [WARN] A365 Copilot summarization cooling down for {remaining:.1f}s after rate limiting; using fallback summaries meanwhile."
                )
            with _state_lock:
                _cooldown_announced = True
        return None

    try:
        max_calls = int(os.getenv("A365_SUMMARY_MAX_CALLS", str(DEFAULT_MAX_CALLS)) or DEFAULT_MAX_CALLS)
    except Exception:
        max_calls = DEFAULT_MAX_CALLS
    with _state_lock:
        if _summaries_requested >= max_calls:
            return None
        _summaries_requested += 1

    normalized_input = _normalize_package_input(package_row)
    payload_text = json.dumps(normalized_input, ensure_ascii=True)

    request_body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You summarize Microsoft 365 Copilot catalog package metadata for readiness reports. "
                    "Return exactly 4 short lines, plain text only, no markdown, no bullets. "
                    "Line 1 must start with 'Package:' and include package name, type/category, and identifier. "
                    "Line 2 must start with 'Purpose/capability:' and explain what it does from available fields. "
                    "Line 3 must start with 'Lifecycle/platform:' and include created/published timing and runtime/platform when present. "
                    "Line 4 must start with 'Status/risk signal:' and summarize status risk from metadata only. "
                    "Never ask for more details, never say information is missing, and never use placeholders like 'not provided'."
                )
            },
            {
                "role": "user",
                "content": f"Summarize this package row for enterprise readers:\n{payload_text}"
            },
        ],
        "temperature": 0.2,
        "max_tokens": 180,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            for attempt in range(MAX_RETRIES):
                response = client.post(DEFAULT_API_URL, json=request_body, headers=headers)

                if response.status_code < 400:
                    text = _extract_text(response.json())
                    if text:
                        if key:
                            with _state_lock:
                                _summary_cache[key] = text
                        with _state_lock:
                            _consecutive_429 = 0
                            _next_allowed_time = 0.0
                            _cooldown_announced = False
                            _api_failure_announced = False
                        return text
                    return None

                # Retry rate limit and transient server errors with backoff.
                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < (MAX_RETRIES - 1):
                        retry_after = _parse_retry_after(response.headers)
                        if retry_after is not None:
                            wait_seconds = retry_after
                        else:
                            base_wait = 1.5 * (attempt + 1)
                            jitter = random.uniform(0.0, 0.8)
                            wait_seconds = base_wait + jitter
                        time.sleep(max(0.5, min(wait_seconds, 8.0)))
                        continue

                if response.status_code == 429:
                    retry_after = _parse_retry_after(response.headers)
                    with _state_lock:
                        _consecutive_429 += 1
                        _cooldown_announced = False
                        cooldown = retry_after
                        if cooldown is None:
                            # Escalating cooldown when retry-after is unavailable.
                            cooldown = min(20.0, 2.0 * (2 ** min(_consecutive_429 - 1, 3))) + random.uniform(0.0, 1.0)
                        _next_allowed_time = time.monotonic() + max(1.0, cooldown)

                    with _state_lock:
                        should_announce = not _api_failure_announced
                        _api_failure_announced = True
                    if should_announce:
                        with _stdout_lock:
                            print(
                                f"\n[{get_timestamp()}] [WARN] A365 Copilot summarization is being rate limited (HTTP 429); temporarily using fallback summaries with adaptive cooldown."
                            )
                    return None

                with _state_lock:
                    _api_disabled = True
                    should_announce = not _api_failure_announced
                    _api_failure_announced = True
                if should_announce:
                    with _stdout_lock:
                        print(
                            f"\n[{get_timestamp()}] [WARN] A365 Copilot summarization disabled after API HTTP {response.status_code}; using fallback summaries."
                        )
                return None
    except Exception:
        with _state_lock:
            _api_disabled = True
            should_announce = not _api_failure_announced
            _api_failure_announced = True
        if should_announce:
            with _stdout_lock:
                print(f"\n[{get_timestamp()}] [WARN] A365 Copilot summarization call failed; using fallback summaries.")
        return None


# Fields extracted from each package row for the executive summarization call.
_EXECUTIVE_SUMMARY_FIELDS = (
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
)


def _aggregate_catalog(packages):
    """Condense a full package list into statistics for the executive summary prompt."""
    from collections import Counter

    rows = [pkg for pkg in (packages if isinstance(packages, list) else []) if isinstance(pkg, dict)]

    types = Counter(str(r.get("type") or "Unknown") for r in rows)
    avail = Counter(str(r.get("availableTo") or "Unknown") for r in rows)
    deployed = Counter(str(r.get("deployedTo") or "Unknown") for r in rows)
    platforms = Counter(str(r.get("platform") or "Not specified") for r in rows)
    publishers = Counter(str(r.get("publisher") or "Unknown") for r in rows)
    blocked = sum(1 for r in rows if r.get("isBlocked") is True)
    names = [str(r.get("displayName") or r.get("name") or "Unknown") for r in rows]

    return {
        "totalPackages": len(rows),
        "byType": dict(types.most_common()),
        "byAvailableTo": dict(avail.most_common()),
        "byDeployedTo": dict(deployed.most_common()),
        "byPlatform": dict(platforms.most_common()),
        "topPublishers": dict(publishers.most_common(15)),
        "blockedCount": blocked,
        "packageNames": names,
    }


def _build_statistical_fallback(agg):
    """Build a plain-text executive summary from aggregated stats when AI is unavailable."""
    total = agg["totalPackages"]
    avail_parts = ", ".join(f"{v} {k}" for k, v in agg["byAvailableTo"].items())
    deploy_parts = ", ".join(f"{v} {k}" for k, v in agg["byDeployedTo"].items())
    platform_parts = ", ".join(f"{k} ({v})" for k, v in list(agg["byPlatform"].items())[:5])
    blocked = agg["blockedCount"]
    blocked_note = f"{blocked} agent(s) are marked as blocked." if blocked else "No agents are currently blocked."

    return (
        f"The Copilot catalog contains {total} agents. "
        f"Availability distribution: {avail_parts}. "
        f"Deployment distribution: {deploy_parts}. "
        f"Platform representation: {platform_parts}. "
        f"{blocked_note} "
        f"Review deployment gaps and blocked entries to assess tenant readiness."
    )


def summarize_catalog_executive(packages):
    """Make a single AI call with aggregated catalog statistics; returns (ai_text_or_None, fallback_text).

    Pre-aggregates the package list to avoid token-limit issues with large catalogs.
    Always returns a non-empty fallback_text derived from statistics so callers
    always have something to put in the report even when the API is unavailable.
    """
    agg = _aggregate_catalog(packages)
    fallback_text = _build_statistical_fallback(agg)

    token, _ = _get_token_cached()
    if not token:
        return None, fallback_text

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    request_body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Microsoft 365 readiness analyst. "
                    "Given aggregated statistics about Copilot catalog agents, "
                    "produce a concise executive summary for an IT admin audience covering: "
                    "the breadth and nature of agents in the catalog, "
                    "the distribution of availability and deployment status (availableTo / deployedTo), "
                    "any blocked or restricted entries, "
                    "notable publishers or platforms represented, "
                    "and overall readiness signals or risks. "
                    "Return plain text only. No markdown, no bullet points, no headers."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize this Copilot catalog for an executive readiness report using the aggregated statistics below:\n"
                    + json.dumps(agg, ensure_ascii=True)
                ),
            },
        ],
        "temperature": 0.3,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            for attempt in range(MAX_RETRIES):
                response = client.post(DEFAULT_API_URL, json=request_body, headers=auth_headers)

                if response.status_code < 400:
                    text = _extract_text(response.json())
                    return (text or None), fallback_text

                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < MAX_RETRIES - 1:
                        retry_after = _parse_retry_after(response.headers)
                        wait = retry_after if retry_after is not None else (1.5 * (attempt + 1)) + random.uniform(0.0, 0.8)
                        time.sleep(max(0.5, min(wait, 15.0)))
                        continue
                break
    except Exception:
        pass

    return None, fallback_text


# ---------------------------------------------------------------------------
# Package detail aggregation helpers
# ---------------------------------------------------------------------------

def _aggregate_details(details):
    """Condense per-package detail list into aggregated statistics."""
    from collections import Counter

    rows = [d for d in (details if isinstance(details, list) else []) if isinstance(d, dict)]

    category_cnt = Counter()
    host_cnt = Counter()
    element_type_cnt = Counter()

    for r in rows:
        for c in (r.get("categories") or []):
            category_cnt[str(c)] += 1
        for h in (r.get("supportedHosts") or []):
            host_cnt[str(h)] += 1
        for e in (r.get("elementTypes") or []):
            element_type_cnt[str(e)] += 1

    return {
        "sampledCount": len(rows),
        "byCategory": dict(category_cnt.most_common()),
        "bySupportedHost": dict(host_cnt.most_common()),
        "byElementType": dict(element_type_cnt.most_common()),
        "byVersion": dict(Counter(str(r.get("version") or "Unknown") for r in rows).most_common(10)),
        "byPlatform": dict(Counter(str(r.get("platform") or "Not specified") for r in rows).most_common()),
        "byAvailableTo": dict(Counter(str(r.get("availableTo") or "Unknown") for r in rows).most_common()),
        "byDeployedTo": dict(Counter(str(r.get("deployedTo") or "Unknown") for r in rows).most_common()),
        "packagesWithRestrictedAccess": sum(
            1 for r in rows
            if isinstance(r.get("allowedUsersAndGroups"), list) and r.get("allowedUsersAndGroups")
        ),
        "packagesWithAcquiredUsers": sum(
            1 for r in rows
            if isinstance(r.get("acquireUsersAndGroups"), list) and r.get("acquireUsersAndGroups")
        ),
    }


def _format_counter_for_text(counter_dict, top=None):
    """Turn {label: count} into 'label (N), label (N)' text."""
    items = list(counter_dict.items())
    if top:
        items = items[:top]
    return ", ".join(f"{k} ({v})" for k, v in items) if items else "None"


def _build_detail_statistical_fallback(agg):
    """Build a plain-text executive detail summary from aggregated statistics."""
    total = agg["sampledCount"]
    cat_parts = _format_counter_for_text(agg["byCategory"], top=8)
    host_parts = _format_counter_for_text(agg["bySupportedHost"])
    elem_parts = _format_counter_for_text(agg["byElementType"])
    restricted = agg["packagesWithRestrictedAccess"]
    acquired = agg["packagesWithAcquiredUsers"]

    restricted_note = (
        f"{restricted} agent(s) have restricted allowedUsersAndGroups policies."
        if restricted
        else "No agents in the sampled set have restricted-access policies."
    )
    acquired_note = (
        f"{acquired} agent(s) show active user acquisition entries."
        if acquired
        else "No active user acquisition entries found in the sampled set."
    )

    return (
        f"Detailed metadata was retrieved for {total} agents. "
        f"Category distribution: {cat_parts}. "
        f"Supported hosts: {host_parts}. "
        f"Element types in use: {elem_parts}. "
        f"{restricted_note} {acquired_note}"
    )


def summarize_details_executive(details):
    """Single AI call with aggregated package detail statistics.

    Returns:
        tuple: (ai_text_or_None, fallback_text)
    """
    agg = _aggregate_details(details)
    fallback_text = _build_detail_statistical_fallback(agg)

    token, _ = _get_token_cached()
    if not token:
        return None, fallback_text

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    request_body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Microsoft 365 readiness analyst and Agent 365 adoption advisor. "
                    "Given aggregated statistics from detailed Copilot catalog agent metadata, "
                    "produce a concise executive summary for an IT admin audience covering: "
                    "the distribution of categories and element types relevant to Agent 365 integration, "
                    "which hosts and platforms are supported (desktop, mobile, web), "
                    "version distribution signals and API compatibility, "
                    "access restriction and user acquisition patterns that affect deployment strategy, "
                    "and recommendations for Agent 365 adoption roadmap including which agents are best-suited for automation. "
                    "Return plain text only. No markdown, no bullet points, no headers."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize this Copilot agent detail analysis for an executive readiness report:\n"
                    + json.dumps(agg, ensure_ascii=True)
                ),
            },
        ],
        "temperature": 0.3,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            for attempt in range(MAX_RETRIES):
                response = client.post(DEFAULT_API_URL, json=request_body, headers=auth_headers)
                if response.status_code < 400:
                    text = _extract_text(response.json())
                    return (text or None), fallback_text
                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < MAX_RETRIES - 1:
                        retry_after = _parse_retry_after(response.headers)
                        wait = retry_after if retry_after is not None else (1.5 * (attempt + 1)) + random.uniform(0.0, 0.8)
                        time.sleep(max(0.5, min(wait, 15.0)))
                        continue
                break
    except Exception:
        pass

    return None, fallback_text


def _build_detail_recommendation_fallback(observation):
    """Build a fallback recommendation when AI is unavailable."""
    return (
        "Review the detailed breakdown of supported hosts, element types, access restrictions, and user acquisition patterns to align "
        "agent deployments with Agent 365 integration requirements. Prioritize agents suitable for automation based on supported hosts "
        "matching your agent target platforms and element type coverage. Use this analysis to create an Agent 365 rollout strategy that "
        "maximizes agent capabilities while respecting access and deployment constraints."
    )


def _ground_recommendation_text(observation, recommendation, fallback):
    """Normalize AI recommendation text to remain evidence-based and observation-grounded."""
    text = (recommendation or "").strip()
    if not text:
        return fallback

    obs = str(observation or "")
    obs_l = obs.lower()
    text_l = text.lower()

    # Only call out explicit issues when the observation itself contains risk/problem signals.
    issue_inference_tokens = ("issue", "problem", "gap", "deficiency")
    evidence_tokens = (
        "error",
        "failed",
        "blocked",
        "deprecated",
        "restriction",
        "restricted",
        "risk",
    )
    has_issue_language = any(t in text_l for t in issue_inference_tokens)
    has_issue_evidence = any(t in obs_l for t in evidence_tokens)
    if has_issue_language and not has_issue_evidence:
        text = re.sub(r"\b[Ii]ssue\b", "pattern", text)
        text = re.sub(r"\b[Pp]roblem\b", "pattern", text)
        text = re.sub(r"\b[Gg]ap\b", "variation", text)
        text = re.sub(r"\b[Dd]eficiency\b", "variation", text)

    # Ensure recommendation remains explicitly Agent 365-oriented.
    if "agent 365" not in text.lower():
        text = f"Use Agent 365 capabilities to act on the observed pattern. {text}"

    # Ensure at least one concrete observed token (version/count) is referenced.
    observed_token = None
    for pattern in (r"\b\d+\.\d+\.\d+\.\d+\b", r"\b\d+\.\d+\.\d+\b", r"\b\d+\b"):
        m = re.search(pattern, obs)
        if m:
            observed_token = m.group(0)
            break
    if observed_token and observed_token not in text:
        text = f"{text} Align actions with the observed distribution markers (for example, {observed_token})."

    return text


def generate_detail_recommendation_from_observation(observation):
    """Generate an AI-based recommendation for Package Detail Overview based on the observation.

    Args:
        observation: The observation text (typically the AI-generated executive summary).

    Returns:
        str: Recommendation text or fallback text if AI is unavailable.
    """
    fallback = _build_detail_recommendation_fallback(observation)

    token, _ = _get_token_cached()
    if not token:
        return fallback

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    request_body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Microsoft 365 and Agent 365 adoption advisor. "
                    "Based on a given observation about Copilot agent details, "
                    "generate a concise, actionable recommendation specifically focused on how Agent 365 can help "
                    "address the exact observation provided. "
                    "Your recommendation should help the customer: "
                    "1) understand the strategic value of Agent 365 for the agents and capabilities observed, "
                    "2) identify deployment priorities that align Agent 365 automation with the agent landscape, "
                    "3) define an Agent 365 adoption roadmap that maximizes value while respecting deployment constraints. "
                    "Do not label something as an issue/problem unless the observation explicitly states a risk/failure signal. "
                    "Reference at least one concrete value from the observation. "
                    "Return plain text only, 3-4 sentences. No markdown, no bullet points, no headers."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Based on this Copilot agent detail observation, generate an Agent 365 adoption recommendation:\n\n"
                    + str(observation)
                ),
            },
        ],
        "temperature": 0.3,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            for attempt in range(MAX_RETRIES):
                response = client.post(DEFAULT_API_URL, json=request_body, headers=auth_headers)

                if response.status_code < 400:
                    text = _extract_text(response.json())
                    if text:
                        return _ground_recommendation_text(observation, text, fallback)
                    return fallback

                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < MAX_RETRIES - 1:
                        retry_after = _parse_retry_after(response.headers)
                        wait = retry_after if retry_after is not None else (1.5 * (attempt + 1)) + random.uniform(0.0, 0.8)
                        time.sleep(max(0.5, min(wait, 15.0)))
                        continue
                break
    except Exception:
        pass

    return fallback


def generate_stat_recommendation_from_observation(feature, observation, fallback):
    """Generate an AI recommendation for a specific stat feature observation.

    Args:
        feature: Stat feature label (for example, Package Detail: Supported Hosts).
        observation: Observation text for that feature.
        fallback: Rule-based fallback recommendation.

    Returns:
        str: AI recommendation when available, otherwise fallback.
    """
    token, _ = _get_token_cached()
    if not token:
        return fallback

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    request_body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Microsoft 365 and Agent 365 adoption advisor. "
                    "Generate one concise recommendation grounded in the provided observation and focused on specific Agent 365 capabilities. "
                    "The recommendation must explicitly connect the observation to practical Agent 365 capabilities such as "
                    "agent orchestration, Teams-based agent delivery, Copilot extensibility, API/webhook integrations, access scope planning, "
                    "or deployment governance. "
                    "Do not infer an issue/problem unless the observation explicitly indicates one. "
                    "Reference at least one concrete value or label from the observation. "
                    "Return plain text only, 2-4 sentences, no markdown, no bullets, no headers."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Feature: {feature}\n"
                    f"Observation: {observation}\n"
                    "Write a recommendation on how Agent 365 can help with this exact observation."
                ),
            },
        ],
        "temperature": 0.3,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            for attempt in range(MAX_RETRIES):
                response = client.post(DEFAULT_API_URL, json=request_body, headers=auth_headers)

                if response.status_code < 400:
                    text = _extract_text(response.json())
                    if text:
                        return _ground_recommendation_text(observation, text, fallback)
                    return fallback

                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < MAX_RETRIES - 1:
                        retry_after = _parse_retry_after(response.headers)
                        wait = retry_after if retry_after is not None else (1.5 * (attempt + 1)) + random.uniform(0.0, 0.8)
                        time.sleep(max(0.5, min(wait, 15.0)))
                        continue
                break
    except Exception:
        pass

    return fallback

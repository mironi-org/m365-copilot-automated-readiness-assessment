"""Generic A365 catalog package recommendation builder."""

from Core.new_recommendation import new_recommendation


def _trim(value, max_len=180):
    """Return a compact single-line representation for report readability."""
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return f"{text[:max_len - 3]}..."


def _package_name(package_row, fallback):
    for key in ("displayName", "name", "title"):
        val = package_row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return fallback or "A365 Package"


def _normalize_text(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _first_present_text(package_row, keys, fallback=""):
    for key in keys:
        value = package_row.get(key)
        if isinstance(value, list):
            joined = ", ".join(_normalize_text(v) for v in value if _normalize_text(v))
            if joined:
                return _trim(joined, max_len=140)
        text = _normalize_text(value)
        if text:
            return _trim(text, max_len=140)
    return fallback


def _extract_capability_signal(package_row):
    """Build a short capability signal from known catalog metadata fields."""
    fields = [
        package_row.get("capabilities"),
        package_row.get("capability"),
        package_row.get("category"),
        package_row.get("type"),
        package_row.get("publisher"),
    ]

    for value in fields:
        if isinstance(value, list) and value:
            text = ", ".join(_normalize_text(v) for v in value if _normalize_text(v))
            if text:
                return _trim(text, max_len=120)
        text = _normalize_text(value)
        if text:
            return _trim(text, max_len=120)

    return "Not surfaced in catalog response"


def _extract_purpose_signal(package_row):
    """Summarize what the agent does from descriptive fields."""
    return _first_present_text(
        package_row,
        (
            "description",
            "shortDescription",
            "longDescription",
            "summary",
            "purpose",
            "capabilityDescription",
        ),
        fallback="Purpose details not surfaced in catalog response",
    )


def _extract_created_signal(package_row):
    """Pull create/publish timing details when available."""
    return _first_present_text(
        package_row,
        (
            "createdDateTime",
            "createdAt",
            "createdOn",
            "publishedDateTime",
            "lastModifiedDateTime",
        ),
        fallback="Creation or publish timestamp not surfaced",
    )


def _extract_platform_signal(package_row):
    """Pull runtime/platform hints (Teams, web, M365 apps, etc.)."""
    return _first_present_text(
        package_row,
        (
            "platform",
            "platforms",
            "runtime",
            "supportedClients",
            "supportedPlatforms",
            "hostProducts",
            "products",
        ),
        fallback="Platform/runtime details not surfaced",
    )


def _guess_platform_from_name(package_name):
    name = _normalize_text(package_name).lower()
    if "outlook" in name:
        return "Outlook"
    if "teams" in name:
        return "Microsoft Teams"
    if "excel" in name:
        return "Excel"
    if "word" in name:
        return "Word"
    if "powerpoint" in name or "ppt" in name:
        return "PowerPoint"
    if "copilot" in name:
        return "Microsoft 365 Copilot"
    return "Microsoft 365"


def _guess_purpose_from_name(package_name):
    name = _normalize_text(package_name).lower()
    rules = (
        (("crm", "sales", "pipeline"), "sales and CRM workflows"),
        (("legal", "contract", "lex", "law"), "legal drafting and contract workflows"),
        (("security", "phish", "threat", "guard"), "security and risk monitoring"),
        (("calendar", "meeting", "schedule"), "scheduling and meeting coordination"),
        (("invoice", "billing", "payment", "finance"), "financial and invoice operations"),
        (("hr", "talent", "recruit", "people"), "HR and talent operations"),
        (("translate", "translator", "language"), "translation and language support"),
        (("signature", "esign", "sign"), "document signing and approval workflows"),
        (("report", "analytics", "dashboard"), "reporting and analytics"),
        (("template", "deck", "presentation"), "document and presentation authoring"),
        (("mail", "email", "outlook"), "email productivity"),
    )

    for keywords, purpose in rules:
        if any(token in name for token in keywords):
            return purpose
    return "general productivity workflows"


def _build_human_fallback_observation(package_name, package_type, package_id, package_status, tags_text, purpose_signal, created_signal, platform_signal, risk_signal):
    """Create a reader-friendly fallback summary when AI output is unavailable."""
    guessed_platform = _guess_platform_from_name(package_name)
    guessed_purpose = _guess_purpose_from_name(package_name)

    has_purpose = "not surfaced" not in _normalize_text(purpose_signal).lower()
    has_platform = "not surfaced" not in _normalize_text(platform_signal).lower()
    has_created = "not surfaced" not in _normalize_text(created_signal).lower()

    purpose_text = purpose_signal if has_purpose else f"it appears aimed at {guessed_purpose}"
    platform_text = platform_signal if has_platform else guessed_platform

    lifecycle_sentence = (
        f"It is intended to run on {platform_text}."
        if not has_created
        else f"It is intended to run on {platform_text}, and catalog lifecycle metadata includes: {created_signal}."
    )

    return (
        f"{package_name} is listed in the Copilot agent catalog as a {package_type} agent (ID: {package_id}), and {purpose_text}.\n"
        f"{lifecycle_sentence}\n"
        f"Current catalog status is '{package_status}'. {risk_signal}. Tags recorded: {tags_text}."
    )


def _extract_risk_signal(package_row, status_text):
    """Derive a basic risk/status signal from agent metadata."""
    status = _normalize_text(status_text) or "Unknown"
    lowered = status.lower()

    if any(word in lowered for word in ("error", "failed", "blocked", "denied", "inactive", "disabled", "deprecated")):
        return f"Status '{status}' may require admin validation before rollout"
    if any(word in lowered for word in ("preview", "beta")):
        return f"Status '{status}' indicates preview behavior; verify tenant readiness"
    if status != "Unknown":
        return f"Status '{status}' reported by catalog"
    return "No explicit risk indicators in returned fields"



def get_recommendation(sku_name, status="Success", client=None):
    """Create one observation recommendation from a single A365 package row."""
    package = client if isinstance(client, dict) else {}

    package_name = _package_name(package, sku_name)
    package_id = _trim(package.get("id") or package.get("packageId") or "Unknown")
    package_type = _trim(package.get("type") or package.get("category") or "Unspecified")
    package_status = _trim(package.get("status") or status or "Unknown")
    capability_signal = _extract_capability_signal(package)
    risk_signal = _extract_risk_signal(package, package_status)
    purpose_signal = _extract_purpose_signal(package)
    created_signal = _extract_created_signal(package)
    platform_signal = _extract_platform_signal(package)

    tags = package.get("tags")
    if isinstance(tags, list):
        tags_text = _trim(", ".join(str(t) for t in tags if t is not None), max_len=120)
    else:
        tags_text = _trim(tags, max_len=120) or "None"

    observation = _build_human_fallback_observation(
        package_name,
        package_type,
        package_id,
        package_status,
        tags_text,
        purpose_signal,
        created_signal,
        platform_signal,
        risk_signal,
    )

    return new_recommendation(
        service="A365",
        feature=package_name,
        observation=observation,
        recommendation="",
        link_text="Copilot Package Catalog API",
        link_url="https://graph.microsoft.com/beta/copilot/admin/catalog/packages",
        status=status or "Success"
    )

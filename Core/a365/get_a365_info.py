"""A365 data processing helpers."""

import asyncio
import importlib

from Core.new_recommendation import new_recommendation
from Core.spinner import _stdout_lock, get_timestamp

_CATALOG_URL = "https://graph.microsoft.com/beta/copilot/admin/catalog/packages"


def _format_distribution(counter_dict, top=None):
    """Turn {label: count} into a readable 'N label, N label' string."""
    items = list(counter_dict.items())
    if top:
        items = items[:top]
    return ", ".join(f"{v} {k}" for k, v in items) if items else "None"


def _stat_recommendations(agg):
    """Convert aggregated catalog stats into individual report rows."""
    total = agg["totalPackages"]
    recs = []

    def _rec(feature, observation):
        recs.append(new_recommendation(
            service="A365",
            feature=feature,
            observation=observation,
            recommendation="",
            link_text="Copilot Package Catalog API",
            link_url=_CATALOG_URL,
            status="Success",
        ))

    # Agent types
    _rec(
        "Catalog: Agent Types",
        f"Of {total} agents in the catalog, the breakdown by type is: {_format_distribution(agg['byType'])}.",
    )

    # Availability
    _rec(
        "Catalog: Availability Distribution",
        f"Agent availability (availableTo) distribution across {total} entries: {_format_distribution(agg['byAvailableTo'])}.",
    )

    # Deployment
    _rec(
        "Catalog: Deployment Distribution",
        f"Agent deployment (deployedTo) distribution across {total} entries: {_format_distribution(agg['byDeployedTo'])}.",
    )

    # Platforms
    _rec(
        "Catalog: Platform Breakdown",
        f"Platforms represented in the catalog: {_format_distribution(agg['byPlatform'])}.",
    )

    # Publishers
    _rec(
        "Catalog: Top Publishers",
        f"Top publishers in the catalog: {_format_distribution(agg['topPublishers'], top=10)}.",
    )

    # Blocked
    blocked = agg["blockedCount"]
    _rec(
        "Catalog: Blocked Agents",
        f"{blocked} of {total} agents are marked as blocked (isBlocked=true)."
        if blocked
        else f"No agents are currently marked as blocked across the {total}-entry catalog.",
    )

    return recs


async def get_a365_info(a365_client, progress_callback=None):
    """Process A365 package catalog payload into orchestrator output format."""
    if not isinstance(a365_client, dict):
        return {
            'available': False,
            'reason': 'A365 catalog payload is unavailable',
            'recommendations': []
        }

    packages = a365_client.get('value', [])
    if not isinstance(packages, list):
        packages = []

    try:
        summarize_module = importlib.import_module("Core.a365.copilot_summarizer")
        get_runtime_mode = getattr(summarize_module, "get_runtime_mode")
        mode = get_runtime_mode()
    except Exception:
        mode = {"enabled": False}

    valid_packages = [package for package in packages if isinstance(package, dict)]
    total_valid = len(valid_packages)

    # One executive-level AI call using pre-aggregated catalog statistics.
    executive_summary = None
    agg = None
    if mode.get("enabled") and total_valid > 0:
        try:
            from Core.a365.copilot_summarizer import _aggregate_catalog, _build_statistical_fallback
            summarize_catalog_executive = getattr(summarize_module, "summarize_catalog_executive")
            agg = _aggregate_catalog(valid_packages)
            ai_text, fallback_text = await asyncio.to_thread(summarize_catalog_executive, valid_packages)
            if ai_text:
                executive_summary = ai_text
            else:
                executive_summary = fallback_text
        except Exception as ex:
            with _stdout_lock:
                print(f"[{get_timestamp()}] [WARN] A365 executive summary failed ({type(ex).__name__}); using statistical fallback.")
            try:
                from Core.a365.copilot_summarizer import _aggregate_catalog, _build_statistical_fallback
                agg = agg or _aggregate_catalog(valid_packages)
                executive_summary = _build_statistical_fallback(agg)
            except Exception:
                executive_summary = f"The Copilot catalog contains {total_valid} agents. Review availability and deployment status for readiness gaps."
    else:
        # No AI token — still produce a statistical observation.
        try:
            from Core.a365.copilot_summarizer import _aggregate_catalog, _build_statistical_fallback
            agg = _aggregate_catalog(valid_packages)
            executive_summary = _build_statistical_fallback(agg)
        except Exception:
            executive_summary = f"The Copilot catalog contains {total_valid} agents."

    recommendations = [
        new_recommendation(
            service="A365",
            feature="Agent Catalog Overview",
            observation=executive_summary,
            recommendation="Use this catalog overview to baseline your Copilot agent landscape and identify which agents could support Agent 365 integration. Review agent types, availability, and deployment patterns to inform your agent automation strategy. Consider license dependencies and deployment scope when planning which agents should be accessible.",
            priority="High",
            link_text="Agent 365 Documentation",
            link_url="https://learn.microsoft.com/en-us/microsoft-agent-365/",
            status="Success",
        )
    ]

    # Append one row per aggregated statistic category.
    if agg:
        recommendations.extend(_stat_recommendations(agg))

    return {
        'available': True,
        'has_a365': True,
        'total_packages': len(packages),
        'packages': packages,
        'recommendations': recommendations
    }

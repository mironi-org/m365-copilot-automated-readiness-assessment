"""A365 package detail data processing helpers.

Receives the list of filtered detail dicts from get_a365_detail_client and
produces one AI executive summary row plus per-category stat observation rows.
"""

import asyncio
import importlib

from Core.new_recommendation import new_recommendation
from Core.spinner import _stdout_lock, get_timestamp

_DETAIL_URL = "https://graph.microsoft.com/beta/copilot/admin/catalog/packages/{id}"

_DETAIL_FEATURE_LINKS = {
    "Agent Detail Overview": (
        "Agent 365 Overview",
        "https://learn.microsoft.com/en-us/microsoft-agent-365/overview",
    ),
    "Agent Detail: Category Distribution": (
        "Agent 365 Capabilities",
        "https://learn.microsoft.com/en-us/microsoft-agent-365/overview",
    ),
    "Agent Detail: Supported Hosts": (
        "Agent 365 Tooling Servers",
        "https://learn.microsoft.com/en-us/microsoft-agent-365/tooling-servers-overview",
    ),
    "Agent Detail: Element Types": (
        "Agent 365 Developer Documentation",
        "https://learn.microsoft.com/en-us/microsoft-agent-365/developer/",
    ),
    "Agent Detail: Version Distribution": (
        "Agent 365 Registration",
        "https://learn.microsoft.com/en-us/microsoft-agent-365/developer/registration",
    ),
    "Agent Detail: Restricted Access": (
        "Agent 365 Access Control",
        "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/capabilities-entra",
    ),
    "Agent Detail: User Acquisition": (
        "Agent 365 Responsible AI",
        "https://learn.microsoft.com/en-us/microsoft-agent-365/admin/responsible-ai-overview",
    ),
}


def _detail_link_for_feature(feature):
    """Return (link_text, link_url) for an A365 detail recommendation feature."""
    return _DETAIL_FEATURE_LINKS.get(
        feature,
        ("Agent 365 Documentation", "https://learn.microsoft.com/en-us/microsoft-agent-365/"),
    )


async def _ai_link_for_feature(feature, observation):
    """Pick a best-fit Agent 365 documentation URL using allowlisted AI selection."""
    fallback_text, fallback_url = _detail_link_for_feature(feature)
    try:
        from Core.a365.copilot_summarizer import choose_agent365_doc_url
        chosen_url = await asyncio.to_thread(
            choose_agent365_doc_url,
            feature,
            observation,
            fallback_url,
        )
        if chosen_url:
            return fallback_text, chosen_url
    except Exception:
        pass
    return fallback_text, fallback_url


def _fmt(counter_dict, top=None):
    """Turn {label: count} into a readable 'N label, N label' string."""
    items = list(counter_dict.items())
    if top:
        items = items[:top]
    return ", ".join(f"{v} {k}" for k, v in items) if items else "None"


async def _stat_detail_recommendations(agg):
    """Build per-category stat recommendation rows from aggregated detail data with Agent 365 guidance."""
    total = agg["sampledCount"]
    rows = []

    def _rec(feature, observation, recommendation, priority):
        rows.append({
            "feature": feature,
            "observation": observation,
            "recommendation": recommendation,
            "priority": priority,
        })

    categories = _fmt(agg['byCategory'])
    _rec(
        "Agent Detail: Category Distribution",
        f"Category distribution across {total} sampled agents: {categories}.",
        f"Review the category breakdown with your Agent 365 adoption team. Prioritize agents in categories aligned with your automation roadmap (e.g., Collaboration, Productivity). See Agent 365 documentation for guidance on mapping agent categories to capabilities.",
        "Medium",
    )

    hosts = _fmt(agg['bySupportedHost'])
    _rec(
        "Agent Detail: Supported Hosts",
        f"Supported host breakdown ({total} agents): {hosts}.",
        f"Ensure your Agent 365 deployment targets support these hosts. Teams-first agents are ideal for agent distribution; desktop apps may require additional client configuration. Validate host requirements in your deployment plan.",
        "Medium",
    )

    elements = _fmt(agg['byElementType'])
    _rec(
        "Agent Detail: Element Types",
        f"Element types observed across {total} agents: {elements}.",
        f"StaticTabs and Bots are common element types in Agent 365 workflows. Plan to extend these agents with capabilities via APIs and webhooks. Refer to Agent 365 extensibility documentation for integration patterns.",
        "Medium",
    )

    versions = _fmt(agg['byVersion'], top=10)
    _rec(
        "Agent Detail: Version Distribution",
        f"Top manifest versions across {total} agents: {versions}.",
        f"Verify that your Agent 365 agents are compatible with the prevalent manifest versions in your tenant. Outdated versions may limit interoperability. Establish a version management policy aligned with Agent 365 updates.",
        "Low",
    )

    restricted = agg["packagesWithRestrictedAccess"]
    _rec(
        "Agent Detail: Restricted Access",
        f"{restricted} of {total} sampled agents have explicit allowedUsersAndGroups restrictions configured."
        if restricted
        else f"None of the {total} sampled agents carry explicit allowedUsersAndGroups restrictions.",
        f"For agents to execute effectively, ensure they have sufficient scope to access required agents. Test Agent 365 user assignments against your agent restrictions to prevent access failures. Document scope requirements in your deployment runbook."
        if restricted
        else f"No restrictions detected on sampled agents, which simplifies Agent 365 scope planning. Verify this applies to your full catalog and adjust agent-level permissions as needed.",
        "High" if restricted else "Low",
    )

    acquired = agg["packagesWithAcquiredUsers"]
    _rec(
        "Agent Detail: User Acquisition",
        f"{acquired} of {total} sampled agents show active user acquisition (non-empty acquireUsersAndGroups)."
        if acquired
        else f"No active user acquisition entries found across the {total} sampled agents.",
        f"These {acquired} agent(s) with active acquired users indicate deployment in progress. Ensure Agent 365 agents gain appropriate permissions for these deployed agents. Coordinate agent capability assignment with ongoing agent rollouts."
        if acquired
        else f"No user acquisition activity detected. Consider leveraging Agent 365 to drive adoption of available agents in your tenant by extending them with agent-driven workflows.",
        "Medium" if acquired else "Low",
    )

    recs = []
    try:
        from Core.a365.copilot_summarizer import generate_stat_recommendation_from_observation
    except Exception:
        generate_stat_recommendation_from_observation = None

    for idx, row in enumerate(rows):
        final_recommendation = row["recommendation"]
        if generate_stat_recommendation_from_observation is not None:
            try:
                # Sequential by design: each recommendation waits for the prior one.
                final_recommendation = await asyncio.to_thread(
                    generate_stat_recommendation_from_observation,
                    row["feature"],
                    row["observation"],
                    row["recommendation"],
                )
                # Gentle pacing between sequential calls to reduce throttling risk.
                if idx < len(rows) - 1:
                    await asyncio.sleep(0.35)
            except Exception:
                final_recommendation = row["recommendation"]

        link_text, link_url = await _ai_link_for_feature(row["feature"], row["observation"])

        recs.append(new_recommendation(
            service="A365",
            feature=row["feature"],
            observation=row["observation"],
            recommendation=final_recommendation,
            link_text=link_text,
            link_url=link_url,
            priority=row["priority"],
            status="Success",
        ))

    return recs


async def get_a365_detail_info(details, progress_callback=None):
    """Process A365 package detail list into orchestrator recommendation rows.

    Args:
        details: List of filtered detail dicts from get_a365_detail_client.
        progress_callback: Optional callable(done, total).

    Returns:
        dict with 'available', 'total_details', and 'recommendations'.
    """
    if not details:
        return {"available": False, "recommendations": []}

    valid_details = [d for d in details if isinstance(d, dict)]
    total = len(valid_details)

    if progress_callback:
        progress_callback(0, total)

    try:
        summarize_module = importlib.import_module("Core.a365.copilot_summarizer")
        mode = getattr(summarize_module, "get_runtime_mode")()
    except Exception:
        mode = {"enabled": False}

    executive_summary = None
    agg = None
    ai_recommendation = None

    if mode.get("enabled") and total > 0:
        try:
            from Core.a365.copilot_summarizer import (
                _aggregate_details,
                _build_detail_statistical_fallback,
                summarize_details_executive,
                generate_detail_recommendation_from_observation,
            )
            agg = _aggregate_details(valid_details)
            ai_text, fallback_text = await asyncio.to_thread(
                summarize_details_executive, valid_details
            )
            executive_summary = ai_text if ai_text else fallback_text
            
            # Generate AI-based recommendation based on observation
            ai_recommendation = await asyncio.to_thread(
                generate_detail_recommendation_from_observation, executive_summary
            )
        except Exception as ex:
            with _stdout_lock:
                print(
                    f"[{get_timestamp()}] [WARN] A365 detail summary failed ({type(ex).__name__}); "
                    "using statistical fallback."
                )
            try:
                from Core.a365.copilot_summarizer import (
                    _aggregate_details,
                    _build_detail_statistical_fallback,
                )
                agg = agg or _aggregate_details(valid_details)
                executive_summary = _build_detail_statistical_fallback(agg)
            except Exception:
                executive_summary = f"Agent detail metadata retrieved for {total} agents."
    else:
        try:
            from Core.a365.copilot_summarizer import (
                _aggregate_details,
                _build_detail_statistical_fallback,
            )
            agg = _aggregate_details(valid_details)
            executive_summary = _build_detail_statistical_fallback(agg)
        except Exception:
            executive_summary = f"Agent detail metadata retrieved for {total} agents."

    # Use AI-generated recommendation if available, otherwise use fallback
    if ai_recommendation is None:
        from Core.a365.copilot_summarizer import _build_detail_recommendation_fallback
        ai_recommendation = _build_detail_recommendation_fallback(executive_summary)

    overview_link_text, overview_link_url = await _ai_link_for_feature(
        "Agent Detail Overview",
        executive_summary,
    )

    recommendations = [
        new_recommendation(
            service="A365",
            feature="Agent Detail Overview",
            observation=executive_summary,
            recommendation=ai_recommendation,
            priority="High",
            link_text=overview_link_text,
            link_url=overview_link_url,
            status="Success",
        )
    ]

    if agg:
        recommendations.extend(await _stat_detail_recommendations(agg))

    if progress_callback:
        progress_callback(total, total)

    return {
        "available": True,
        "total_details": total,
        "recommendations": recommendations,
    }

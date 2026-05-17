# Change Activity: GitHub CLI Check — Hard Blocker → Soft Warning

**Started:** 2026-05-17  
**Status:** PENDING  
**Component:** `Core/orchestrator.py` (lines 44–48)

---

## Problem

The A365 pre-flight check in `orchestrator.py` treats GitHub CLI availability as a **hard gate**.  
If `gh` is not installed or not authenticated, the entire A365 pipeline is blocked (`return`).

GitHub CLI is only used by `Core/a365/copilot_summarizer.py` to obtain a token for the  
GitHub Models API (`models.inference.ai.azure.com`) — an **optional AI summarization** feature.  
The core A365 data collection (PowerShell `Connect-MgGraph` → Graph API) does **not** need it.

`copilot_summarizer.py` already has fallback paths (`_build_statistical_fallback`,  
`_build_detail_recommendation_fallback`) that produce recommendations without the API.

## Fix

Convert the hard gate to a soft warning so A365 catalog collection always proceeds.

### File: `Core/orchestrator.py`

**BEFORE (lines 44–48):**
```python
        # PRE-FLIGHT: Ensure GitHub CLI is ready if A365 is selected
        if run_a365:
            from .a365.github_cli_setup import ensure_github_cli_ready
            if not ensure_github_cli_ready():
                print(f"\n[{get_timestamp()}] ❌ A365 service requires GitHub Copilot API access via GitHub CLI.")
                return
```

**AFTER:**
```python
        # PRE-FLIGHT: Check GitHub CLI for optional AI summaries (A365)
        if run_a365:
            from .a365.github_cli_setup import ensure_github_cli_ready
            if not ensure_github_cli_ready():
                print(f"\n[{get_timestamp()}] ⚠️  GitHub CLI not available — AI-powered summaries will be skipped.")
                print(f"[{get_timestamp()}]    Core A365 catalog data collection will proceed normally.")
```

## Rollback

Restore the hard gate by reverting `Core/orchestrator.py` lines 44–48 to the BEFORE block above.

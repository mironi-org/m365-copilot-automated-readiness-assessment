# CHANGE LOG — Purview Auth Consolidation (5 device codes → 1)
# Implemented: 2026-05-14
# Goal: Consolidate 5 Purview device-code prompts into 1 using MSAL token sharing

---

## Summary

All 4 files modified. Zero errors on validation.

### File 1: Core/get_graph_client.py (3 changes)
1. **Added `import msal`** after `from msgraph import GraphServiceClient`
2. **Added `acquire_purview_tokens()` function** + `_purview_tokens` dict + scope constants between `_create_interactive_credential()` and `get_graph_client()`. One MSAL device-code flow → silent acquisition for EXO + IPPS scopes.
3. **Added `_StaticTokenCredential` conditional** in credential creation block — when Purview tokens exist and CLIENT_ID_STREAM3 matches, uses static bearer token instead of DeviceCodeCredential.

### File 2: Core/orchestrator_powershell.py (3 changes)
1. **Function start rewritten** — acquires EXO+IPPS tokens via `acquire_purview_tokens()` before launching PS; builds cmd with `-ExoToken`/`-IppsToken` args when available; falls back gracefully on failure.
2. **Spinner/stdout simplified** — shows "Collecting Purview compliance data..." when tokens pre-acquired; device-code detection only in fallback mode.
3. **Stderr AUTH_COMPLETE handler updated** — changed "authentication accepted" → "connected"; SCC auth prompt only when `not ipps_token`; resumes spinner after each service connects.

### File 3: collect_purview_data.ps1 (4 changes)
1. **Param block** — added `[string]$ExoToken = ""` and `[string]$IppsToken = ""`.
2. **EXO Connect** — added `if ($ExoToken -ne "")` branch using `Connect-ExchangeOnline -AccessToken $ExoToken`.
3. **IPPS Connect** — added `if ($IppsToken -ne "")` branch using `Connect-IPPSSession -AccessToken $IppsToken`.
4. **Catch block** — removed stray `python main.py --auth-mode device_code --services Purview` line (existing bug).

### File 4: requirements.txt (1 change)
1. **Added `msal>=1.20.0`** after `azure-core>=1.29.0`.

---

## Rollback
Refer to `logs/PREVIEW-CHANGE-Purview-Auth-Consolidation.md` for exact old/new code blocks.

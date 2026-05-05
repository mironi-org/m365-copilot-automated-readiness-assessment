# Implementation Plan: Interactive Auth Without App Registration

## Objective
Simplify interactive authentication by using a well-known Microsoft first-party client ID, eliminating the need for a custom app registration entirely.

---

## Key Insight

`InteractiveBrowserCredential` can use **well-known first-party Microsoft client IDs** that are already registered and pre-consented in every Azure AD tenant. The user only needs their **directory role** — no Application Administrator, no app registration, no admin consent flow.

### Well-Known Client ID Selected

| Client ID | App Name | Reason |
|-----------|----------|--------|
| `14d82eec-204b-4c2f-b7e8-296a70dab67e` | **Microsoft Graph PowerShell** | Pre-registered in all tenants, broadest Graph scope coverage, delegated permissions already consented in most orgs |

### Comparison: Custom App vs Well-Known Client

| Aspect | Custom App Registration (old) | Well-Known Client ID (new) |
|--------|-------------------------------|---------------------------|
| Setup steps | Run `setup-interactive-auth.ps1`, create app, grant admin consent | None — just set `TENANT_ID` |
| Admin role needed | Application Administrator | None (user only needs Global Reader) |
| Admin consent | Required before first use | Already granted in most tenants |
| `.env` requirements | `TENANT_ID` + `CLIENT_ID` + `AUTH_MODE` | `TENANT_ID` only |
| First-run experience | Complex (app reg + consent + env file) | Immediate (browser login) |

---

## User Prerequisites (Interactive Mode)

| Requirement | Details |
|------------|---------|
| Azure AD role | **Global Reader** (for full M365 + Entra assessment) |
| Local machine | Browser available for login |
| `.env` file | Only `TENANT_ID` required |

---

## Files to Modify

| # | File | Change |
|---|------|--------|
| 1 | `Core/credentials_check.py` | When `AUTH_MODE=interactive`, only require `TENANT_ID` (skip `CLIENT_ID` check) |
| 2 | `Core/get_graph_client.py` | Use hardcoded well-known client ID `14d82eec-204b-4c2f-b7e8-296a70dab67e` when no `CLIENT_ID` in env |
| 3 | `Core/cli_parser.py` | Already done — `--auth-mode interactive` sets `AUTH_MODE` env var |

---

## Detailed Changes

### 1. `Core/credentials_check.py`

```python
def check_credentials():
    load_env_file()
    auth_mode = os.environ.get('AUTH_MODE', 'service_principal')
    
    missing = []
    if not os.environ.get('TENANT_ID'):
        missing.append('TENANT_ID')
    
    # Interactive mode: only TENANT_ID required (uses well-known client ID)
    if auth_mode != 'interactive':
        if not os.environ.get('CLIENT_ID'):
            missing.append('CLIENT_ID')
        if not os.environ.get('CLIENT_SECRET'):
            missing.append('CLIENT_SECRET')
    
    return missing
```

### 2. `Core/get_graph_client.py`

```python
# Well-known Microsoft Graph PowerShell client ID (pre-registered in all tenants)
GRAPH_POWERSHELL_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"

if auth_mode == 'interactive':
    client_id = os.getenv('CLIENT_ID') or GRAPH_POWERSHELL_CLIENT_ID
    
    _credential = InteractiveBrowserCredential(
        tenant_id=tenant_id,
        client_id=client_id
    )
```

### 3. `setup-interactive-auth.ps1`

**Deleted** — no longer needed. Interactive mode uses the well-known Graph PowerShell client ID by default.

---

## New User Flow (Interactive Mode)

```
1. User creates .env:
   TENANT_ID=<their-tenant-id>

2. User runs:
   python main.py --auth-mode interactive --services M365 Entra

3. Browser opens → user logs in with MFA → assessment runs
```

No app registration. No admin consent. No CLIENT_ID or CLIENT_SECRET.

---

## Potential Issues & Mitigations

| Issue | Impact | Mitigation |
|---|---|---|
| Org blocks Graph PowerShell app | Login fails with consent error | User can override with custom `CLIENT_ID` in `.env` (falls back to old flow) |
| Tenant requires admin consent for all apps | First-time consent prompt fails | Admin must consent once: `https://login.microsoftonline.com/{tenant}/adminconsent?client_id=14d82eec-204b-4c2f-b7e8-296a70dab67e` |
| Headless/remote server | No browser | Future: add `DeviceCodeCredential` fallback |
| Token lifetime (~1 hour) | Long assessments may timeout | Unlikely for this tool's runtime (~5 min) |

---

## Execution Order

1. Modify `Core/credentials_check.py` — skip `CLIENT_ID` check when interactive
2. Modify `Core/get_graph_client.py` — default to well-known client ID when `CLIENT_ID` not set
3. Update `Core/get_graph_client.py` `get_shared_credential()` with same logic
4. Test: `python main.py --auth-mode interactive --services M365 Entra` with only `TENANT_ID` in `.env`
5. ~~Update `setup-interactive-auth.ps1` header to mark it as optional~~ → Deleted the script entirely

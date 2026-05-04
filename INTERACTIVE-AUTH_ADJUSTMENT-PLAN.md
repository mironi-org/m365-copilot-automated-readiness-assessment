# Implementation Plan: InteractiveBrowserCredential Auth Mode

## Objective
Add `InteractiveBrowserCredential` as an alternative authentication method alongside existing service principal auth.

---

## Analysis Summary

### Current Authentication Architecture

The tool uses a **hybrid auth model**:

| Services | Current Auth Method | Mechanism |
|----------|-------------------|-----------|
| M365, Entra, Defender | Service Principal (app-only) | `ClientSecretCredential` with `TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET` from `.env` |
| Power Platform, Copilot Studio | User delegated | PowerShell subprocess with interactive browser sign-in |
| Purview | User delegated | PowerShell subprocess using `Connect-IPPSSession` |
| A365 | User delegated | PowerShell `Connect-MgGraph` with device code auth |

The core Graph client (`Core/get_graph_client.py`) creates a `ClientSecretCredential` and passes it to `GraphServiceClient` with scope `https://graph.microsoft.com/.default`. The same credential is reused for Defender API and Power Platform API.

### User Auth Options Evaluated

| Credential | MFA Support | Secrets in .env | Browser Required | Verdict |
|---|---|---|---|---|
| `InteractiveBrowserCredential` | ✅ Full | ❌ None | ✅ Yes | **Selected** |
| `DeviceCodeCredential` | ✅ Full | ❌ None | ❌ No (any device) | Good for headless |
| `AzureCliCredential` | ✅ Full | ❌ None | ❌ No (`az login` first) | Simplest but requires CLI |
| `AzurePowerShellCredential` | ✅ Full | ❌ None | ❌ No (`Connect-AzAccount` first) | PS-only |
| `UsernamePasswordCredential` | ❌ Blocked by MFA | ⚠️ Password in plaintext | ❌ No | **Rejected** — worse than SP |

### Why `InteractiveBrowserCredential` Was Chosen

| Pros | Cons |
|---|---|
| ✅ MFA compatible | ❌ Still needs app registration |
| ✅ No secrets stored anywhere | ❌ Requires local browser (not headless) |
| ✅ Familiar login UX for users | ❌ User needs Global Reader role |
| ✅ Token cached for entire session | ❌ Admin must pre-consent delegated perms |
| ✅ Works with Conditional Access policies | ❌ Slightly less data than app permissions on some endpoints |

### How `InteractiveBrowserCredential` Works

1. Script starts → browser opens to Microsoft login page
2. User logs in with username + password + completes MFA
3. Token returned to script via localhost redirect → continues execution
4. Token cached in memory for the session (no re-prompt for subsequent API calls)

### Delegated Permission Considerations

The current service principal uses **Application** permissions (tenant-wide access without signed-in user). With **Delegated** permissions:

- `User.Read.All` — works, but user needs Directory Reader role
- `SecurityEvents.Read.All` — works with Security Reader role
- `Reports.Read.All` — ⚠️ usage reports require **Global Reader** role for delegated access
- `RoleManagement.Read.Directory` — works with Global Reader
- `AuditLog.Read.All` — requires Global Reader or Reports Reader

**Conclusion**: The signed-in user needs **Global Reader** role for full feature parity with the service principal.

### Potential Issues

| Issue | Impact | Mitigation |
|---|---|---|
| Headless/remote server | No browser → fails | Use `DeviceCodeCredential` instead (future enhancement) |
| Token lifetime | ~1 hour; long assessments may need re-auth | Unlikely for this tool's run time |
| Port conflict | Localhost redirect needs free port | Rare; retry on different port |
| Consent not granted | First run fails | Admin must pre-consent delegated permissions |
| Delegated vs Application perms | Some endpoints return less data | User needs Global Reader role |

---

## Files to Modify

| # | File | Change Description |
|---|------|-------------------|
| 1 | `Core/cli_parser.py` | Add `--auth-mode` argument (choices: `service_principal`, `interactive`) |
| 2 | `Core/credentials_check.py` | Skip `CLIENT_SECRET` validation when `AUTH_MODE=interactive` |
| 3 | `Core/get_graph_client.py` | Add `InteractiveBrowserCredential` branch based on `AUTH_MODE` |

## Backup Strategy
Each file will be copied to `<filename>_orig.py` before modification.

---

## Detailed Changes

### 1. `Core/cli_parser.py`
- Add `--auth-mode` argument with choices `service_principal` (default), `interactive`
- Pass value into parsed args

### 2. `Core/credentials_check.py`
- Read `AUTH_MODE` from environment (or accept as parameter)
- When `AUTH_MODE=interactive`: only require `TENANT_ID` + `CLIENT_ID`
- When `AUTH_MODE=service_principal` (default): require all 3 (TENANT_ID, CLIENT_ID, CLIENT_SECRET)

### 3. `Core/get_graph_client.py`
- Import `InteractiveBrowserCredential` from `azure.identity`
- Read `AUTH_MODE` from environment
- If `interactive`: create `InteractiveBrowserCredential(tenant_id=..., client_id=...)`
- If `service_principal` (default): keep existing `ClientSecretCredential` logic unchanged
- Update `get_shared_credential()` with same logic

---

> **Full execution guidelines, stream architecture, permissions, and prerequisites have been moved to [`exec-guidelines.md`](exec-guidelines.md)**

---

## Execution Order
1. ✅ Create this planning file
2. ✅ Create `setup-interactive-auth.ps1` (automated app registration + delegated permissions per stream)
3. ✅ Approval granted
4. ✅ Copy `Core/cli_parser.py` → `Core/cli_parser_orig.py`
5. ✅ Copy `Core/credentials_check.py` → `Core/credentials_check_orig.py`
6. ✅ Copy `Core/get_graph_client.py` → `Core/get_graph_client_orig.py`
7. ✅ Modify `Core/cli_parser.py` — added `--auth-mode` argument (choices: `service_principal`, `interactive`), env fallback logic, sets `AUTH_MODE` env var
8. ✅ Modify `Core/credentials_check.py` — skips `CLIENT_SECRET` when `AUTH_MODE=interactive`, updated error message with both setup options
9. ✅ Modify `Core/get_graph_client.py` — added `InteractiveBrowserCredential` import, branching in `get_graph_client()` and `get_shared_credential()` based on `AUTH_MODE`
10. ✅ Validation tests passed (cli_parser arg handling, credentials_check branching, credential instantiation, invalid input rejection)

---

## Implementation Notes

- `redirect_uri` is **not** passed to `InteractiveBrowserCredential` — the SDK auto-selects a free localhost port. The app registration's `http://localhost` redirect (mobile/desktop platform) matches any localhost port for public clients.
- The `--auth-mode` CLI argument takes priority over `AUTH_MODE` env var. If neither is set, defaults to `service_principal`.
- `AUTH_MODE` is written to `os.environ` by `cli_parser.py` so that downstream modules (`credentials_check.py`, `get_graph_client.py`) can read it without parameter passing.
- Backup files created: `cli_parser_orig.py`, `credentials_check_orig.py`, `get_graph_client_orig.py`

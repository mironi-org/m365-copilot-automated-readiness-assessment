# Change Activity: Stream 5 (A365/Copilot) — Dedicated App Registration

| Field | Value |
|---|---|
| **Started** | 2026-05-14 |
| **Status** | 🔄 IN PROGRESS |
| **Scope** | Stream 5 (A365/Copilot) authentication — add dedicated app registration like Streams 1–4 |
| **Root Cause** | Stream 5 uses `Connect-MgGraph` without a dedicated app registration, so `CopilotPackages.Read.All` is never admin-consented. Users get "Signed-in user is not authorized for Copilot admin catalog endpoint" (HTTP 403). |

---

## Problem

When running `python main.py --auth-mode device_code --services A365`, Stream 5 connects via `Connect-MgGraph` using the **generic Microsoft Graph PowerShell app** (`14d82eec-204b-4c2f-b7e8-296a70dab67e`). This app does NOT have `CopilotPackages.Read.All` consented, so the Copilot admin catalog endpoint returns 403.

Streams 1–4 each have their own app registration with pre-consented permissions. Stream 5 was the only stream without one.

---

## Solution

Create a dedicated app registration for Stream 5 (`CLIENT_ID_STREAM5`) with:
- **CopilotPackages.Read.All** (delegated) — `a2dcfcb9-cbe8-4d42-812d-952e55cf7f3f`
- **User.Read** (delegated) — `e1fe6dd8-ba31-4d61-89e7-88639da4683d`

Then pass `-ClientId` to all `Connect-MgGraph` calls for Stream 5, and grant admin consent via the setup script.

---

## Files Changed

### 1. `setup-interactive-auth.ps1`

**BEFORE:** Only creates Streams 1–4. `$selectedStreams = @(1, 2, 3, 4)`. No Stream 5 config, permissions, creation, consent, or .env writing.

**AFTER:** Adds Stream 5 to `$streamConfig`, defines `$stream5Permissions`, creates the app, grants admin consent, writes `CLIENT_ID_STREAM5` to `.env`.

### 2. `Core/a365/get_a365_client.py`

**BEFORE:** `Connect-MgGraph` called without `-ClientId`. On 403, opens consent URL for generic MS Graph PS app `14d82eec-204b-4c2f-b7e8-296a70dab67e`.

**AFTER:** Reads `CLIENT_ID_STREAM5` from env. Passes `-ClientId $clientId` to `Connect-MgGraph`. Removes consent URL fallback (no longer needed — consent is handled by setup script).

### 3. `Core/get_graph_client.py` — `ensure_a365_interactive_signin()`

**BEFORE:** `Connect-MgGraph` called without `-ClientId`.

**AFTER:** Reads `CLIENT_ID_STREAM5` from env. Passes `-ClientId $clientId` to `Connect-MgGraph`.

### 4. `INTERACTIVE-AUTH-GUIDELINES.md`

**BEFORE:** Stream 5 documented as "no app registration needed", env var shown as `*(none — uses Connect-MgGraph)*`.

**AFTER:** Stream 5 documented with `CLIENT_ID_STREAM5`, same pattern as Streams 1–4.

---

## Bug Fix: `--auth-mode device_code` ignored by A365 (2026-05-14)

**Symptom:** Running `--auth-mode device_code --services A365` opened a WAM browser popup instead of showing a device code prompt.

**Root Cause:** Both `get_a365_client()` and `ensure_a365_interactive_signin()` did not check the `USE_DEVICE_CODE` environment variable (set by `--auth-mode device_code` in `cli_parser.py`).

- `get_a365_client.py`: Always tried browser popup first (`Connect-MgGraph` without `-UseDeviceAuthentication`), falling back to device code only on failure.
- `ensure_a365_interactive_signin()`: Always used `-UseDeviceAuthentication` regardless of auth mode.

**Fix (2 files):**

### `Core/a365/get_a365_client.py`
- Added `use_device_code = os.getenv('USE_DEVICE_CODE') == '1'` check
- **device_code mode**: Uses `-UseDeviceAuthentication` directly, no browser popup
- **interactive mode**: Tries browser popup first, falls back to device code on failure

### `Core/get_graph_client.py` — `ensure_a365_interactive_signin()`
- Added same `USE_DEVICE_CODE` check
- **device_code mode**: Uses `-UseDeviceAuthentication` directly
- **interactive mode**: Uses browser popup (`Connect-MgGraph` without `-UseDeviceAuthentication`)

---

## Bug Fix: Missing `try {` in PS command after device-code split (2026-05-14)

**Symptom:** `ParserError: Unexpected token '}' in expression or statement` when running `--auth-mode device_code --services A365`. PowerShell fails immediately, A365 data gathering skipped.

**Root Cause:** When the device-code/interactive branching was added, the common API-call section (`Invoke-MgGraphRequest ... exit 0 } catch { ... }`) lost its opening `try {`. The `}` and `catch {` appeared without a matching `try`, causing a PS parse error.

**Fix (2 files):**
- `Core/a365/get_a365_client.py`: Added `"try {"` at the start of the common `ps_command +=` block
- `Core/get_graph_client.py` — `ensure_a365_interactive_signin()`: Same fix

---

## Fix 4: Diagnostic output + scope mismatch fix (2026-05-14)

**Root Cause:** After device code auth completed successfully, the Copilot admin catalog endpoint returned HTTP 403. However, the PS `catch` block only returned exit codes without outputting the actual error message/body. This made it impossible to diagnose whether the 403 was due to missing consent, missing license, or a different server-side issue. Additionally, `$scopes` included `Directory.Read.All` which was NOT declared in the app's `requiredResourceAccess`.

**Changes made:**

### `Core/a365/get_a365_client.py`
1. **Removed `Directory.Read.All` from `$scopes`** — the app registration only declares `User.Read` + `CopilotPackages.Read.All`; requesting an undeclared scope could confuse token issuance
2. **Added diagnostic output after Connect-MgGraph** — shows the authenticated account, token scopes, and auth type (`[A365-DIAG]` prefix) so we can verify what the token actually contains
3. **Added error details in PS catch block** — now writes the actual exception message, HTTP status code, and response body before exiting, prefixed with `[A365-DIAG]`
4. **Improved Python error messages** — differentiates 401 vs 403 vs 51 (non-HTTP), references `[A365-DIAG]` output, lists possible causes for 403

### `Core/get_graph_client.py` — `ensure_a365_interactive_signin()`
1. Same scope fix — removed `Directory.Read.All` from both device-code and interactive branches
2. Same diagnostic output — token scopes after Connect, error details in catch block

---

## Rollback Instructions

1. Revert all 4 files to their prior state (git checkout or manual)
2. In Azure Portal → Entra ID → App registrations → delete "Readiness - A365/Copilot"
3. Remove `CLIENT_ID_STREAM5=...` from `.env`
4. Stream 5 will revert to using generic Connect-MgGraph (with the 403 issue)

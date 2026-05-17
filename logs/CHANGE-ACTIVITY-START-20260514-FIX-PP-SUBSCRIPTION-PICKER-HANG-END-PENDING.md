# CHANGE LOG — Power Platform Subscription Picker Hang Fix
# Started: 2026-05-14
# Status: IMPLEMENTED (2026-05-14 14:20)
# Goal: Fix Connect-AzAccount hanging on subscription selection when user has multiple Azure subscriptions
# Root Cause: Connect-AzAccount -UseDeviceAuthentication triggers an interactive subscription
#   picker when the authenticated account has access to multiple Azure subscriptions.
#   The PowerShell script runs as a subprocess with stdout=subprocess.PIPE (in
#   Core/orchestrator_powershell.py line 31), so the picker renders to captured output
#   but user keyboard input cannot reach the subprocess stdin — causing a permanent hang.
# Impact: Tool hangs indefinitely after device-code authentication when user has 2+ subscriptions.
# Reproduction: Authenticated with account having access to subscriptions "Sandbox--2" and "Sundbox--1".
#   After device-code auth, Connect-AzAccount displayed:
#     [Tenant and subscription selection]
#     No    Subscription name    Subscription ID                          Tenant name
#     ----  -------------------  ---------------------------------------- -----------
#     [1]   Sandbox--2           672787cf-5e1a-4ced-8b67-a47373c34bf3
#     [2]   Sundbox--1           08c461fa-0b57-41fd-b084-90cc19431ecc
#   ...and waited for input that could never arrive through the piped subprocess.

---

## FILE 1: collect_power_platform_and_copilot_studio_data.ps1

### CHANGE 1A: Add -SkipContextPopulation to Connect-AzAccount (line 76)

**Rationale:**
- `-SkipContextPopulation` tells Connect-AzAccount to skip subscription/tenant enumeration
  after authentication, so no interactive picker is shown.
- The PP script NEVER uses ARM subscription context — it only calls
  `Get-AzAccessToken -ResourceUrl` for BAP and Flow API tokens.
- `Get-AzAccessToken` works with `-SkipContextPopulation` because it uses the
  authenticated session's refresh token to request tokens for specific resources.
- This is a safe, non-breaking change — no other behavior is affected.

**BEFORE (line 76):**
```powershell
        Connect-AzAccount -Tenant $TenantId -UseDeviceAuthentication -ErrorAction Stop -WarningAction SilentlyContinue
```

**AFTER:**
```powershell
        # -SkipContextPopulation prevents interactive subscription picker that hangs in subprocess
        Connect-AzAccount -Tenant $TenantId -UseDeviceAuthentication -SkipContextPopulation -ErrorAction Stop -WarningAction SilentlyContinue
```

---

## ROLLBACK INSTRUCTIONS

To revert this change, restore line 76 of `collect_power_platform_and_copilot_studio_data.ps1` to:
```powershell
        Connect-AzAccount -Tenant $TenantId -UseDeviceAuthentication -ErrorAction Stop -WarningAction SilentlyContinue
```
Remove the comment line above it that mentions `-SkipContextPopulation`.

**Note:** Rolling back will re-introduce the subscription picker hang for users with multiple
Azure subscriptions. Only roll back if `-SkipContextPopulation` causes issues with
`Get-AzAccessToken -ResourceUrl` for BAP/Flow tokens (unlikely based on documentation).

---

## RISK ASSESSMENT

- **Risk Level:** Very Low
- **Affected file(s):** 1 file — `collect_power_platform_and_copilot_studio_data.ps1`
- **Affected line(s):** Line 76 (one-line change)
- **Side effects:** None — the script does not use `Get-AzSubscription`, `Get-AzResource`, 
  or any subscription-scoped ARM operations
- **Tested commands after fix:** `Get-AzAccessToken -ResourceUrl "https://api.bap.microsoft.com"` 
  and `Get-AzAccessToken -ResourceUrl "https://service.flow.microsoft.com"` — both expected 
  to work identically with `-SkipContextPopulation`

---

## FILE 2: INTERACTIVE-AUTH-GUIDELINES.md (documentation corrections)

### CHANGE 2A: Stream 4 "How it works" section (line ~242)

**BEFORE:**
```markdown
> **How Stream 4 works:** Stream 4 authenticates in two steps:
> 1. **Graph API** — uses `CLIENT_ID_STREAM4` to acquire a Graph token (for `Organization.Read.All` license queries)
> 2. **Power Platform API** — launches a PowerShell subprocess that runs `Connect-AzAccount` (from `Az.Accounts` module) to access Power Platform environments and policies
>
> In **device code** mode, you will see **two separate device code prompts** — complete each one in order.
```

**AFTER:**
```markdown
> **How Stream 4 works:** Stream 4 authenticates in two steps:
> 1. **Power Platform API** — launches a PowerShell subprocess that runs `Connect-AzAccount` (from `Az.Accounts` module) to access Power Platform environments and policies
> 2. **Graph API** — uses `CLIENT_ID_STREAM4` to acquire a Graph token (for `Organization.Read.All` license queries)
>
> In **device code** mode, you will see **two separate device code prompts**. After each authentication, the tool proceeds automatically to the next step.
```

### CHANGE 2B: Interactive mode Stream 4 comment (line ~315)

**BEFORE:**
```powershell
# NOTE: Stream 4 triggers TWO auth prompts:
#   1) Graph API (for Organization.Read.All license queries)
#   2) Connect-AzAccount (for Power Platform API access)
```

**AFTER:**
```powershell
# NOTE: Stream 4 triggers TWO auth prompts:
#   1) Connect-AzAccount (for Power Platform API access via Az.Accounts)
#   2) Graph API (for Organization.Read.All license queries)
# After each authentication, the tool proceeds automatically to the next step.
```

### CHANGE 2C: Device code mode Stream 4 comment (line ~344)

**BEFORE:**
```powershell
# NOTE: Stream 4 triggers TWO device code prompts:
#   1) Graph API device code (for Organization.Read.All license queries)
#   2) Connect-AzAccount device code (for Power Platform API access via Az.Accounts)
# Complete each device code prompt in order before proceeding.
```

**AFTER:**
```powershell
# NOTE: Stream 4 triggers TWO device code prompts:
#   1) Connect-AzAccount device code (for Power Platform API access via Az.Accounts)
#   2) Graph API device code (for Organization.Read.All license queries)
# After each authentication, the tool proceeds automatically to the next step.
```

---

## ROLLBACK INSTRUCTIONS (DOCUMENTATION)

To revert documentation changes, restore the original order (Graph first, Connect-AzAccount second)
and original wording ("complete each one in order" / "Complete each device code prompt in order before proceeding")
in all 3 locations in `INTERACTIVE-AUTH-GUIDELINES.md`.

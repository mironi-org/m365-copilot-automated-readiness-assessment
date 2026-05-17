# CHANGE LOG — Stream 4 Permissions + Double Device-Code Prompt Fix
# Started: 2026-05-14 00:15:00
# Ended: 2026-05-14 00:18:00
# Status: COMPLETED
# Goal: (1) Fix double device-code prompt by forcing eager token acquisition in get_graph_client()
#        (2) Add Organization.Read.All Graph permission to Stream 4 documentation
#        (3) Note setup-interactive-auth.ps1 requires manual update for Stream 4

---

## PROBLEM SUMMARY

### Problem 1: Double device-code prompt
When running `python main.py --auth-mode device_code --services M365`:
1. `analyze_service_plans()` → `get_graph_client()` → creates DeviceCodeCredential → prints "✅ Authenticated successfully" **BEFORE** any real auth happens (GraphServiceClient constructor is lazy)
2. `subscribed_skus.get()` triggers first device code prompt (e.g. CVFHPPYWH)
3. If that call fails (caught silently as "skipped - no license permission"), token is not cached
4. `setup_graph_and_licenses()` → reuses cached client → `subscribed_skus.get()` → triggers SECOND device code prompt (e.g. GGTQWGY46)

**Root cause:** `get_graph_client()` never forces token acquisition — it returns before the user has actually authenticated.

### Problem 2: Stream 4 missing Graph permissions
CLIENT_ID_STREAM4 app only has `user_impersonation` on Power Platform API — zero Graph permissions.
When the code creates a Graph client for Power Platform, `subscribed_skus.get()` fails because the app can't access Graph.
The admin consent page doesn't prompt because consent was already granted (from a prior run), but the permission itself is insufficient.

---

## FILE 1: Core/get_graph_client.py

### CHANGE 1A: Force eager token acquisition before returning GraphServiceClient

**BEFORE (lines 128-160):**
```python
        # Check cache (per client_id)
        if client_id in _graph_clients:
            return _graph_clients[client_id]
        
        use_device_code = os.getenv('USE_DEVICE_CODE') == '1'
        if not silent:
            method = 'device code flow' if use_device_code else 'interactive browser login'
            print(f"[{get_timestamp()}] ℹ️     Authenticating with {method}...")
            import sys
            sys.stdout.flush()
        
        if client_id not in _credentials:
            _credentials[client_id] = _create_interactive_credential(tenant_id, client_id)
        
        credential = _credentials[client_id]
        
        # For interactive with per-stream apps: use .default (admin pre-granted consent)
        scopes = ['https://graph.microsoft.com/.default']
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=scopes
        )
        
        _graph_clients[client_id] = graph_client
        
        if not silent:
            print(f"[{get_timestamp()}] ✅ Authenticated successfully")
            import sys
            sys.stdout.flush()
        
        return graph_client
```

**AFTER:**
```python
        # Check cache (per client_id)
        if client_id in _graph_clients:
            return _graph_clients[client_id]
        
        use_device_code = os.getenv('USE_DEVICE_CODE') == '1'
        if not silent:
            method = 'device code flow' if use_device_code else 'interactive browser login'
            print(f"[{get_timestamp()}] ℹ️     Authenticating with {method}...")
            import sys
            sys.stdout.flush()
        
        if client_id not in _credentials:
            _credentials[client_id] = _create_interactive_credential(tenant_id, client_id)
        
        credential = _credentials[client_id]
        
        # Force token acquisition NOW — triggers the device code prompt or browser
        # popup immediately, ensures "Authenticated" prints only after real auth,
        # and caches the token so subsequent API calls reuse it (no double prompts).
        # Wrapped in try/except because some stream apps (e.g. Stream 4 Power Platform)
        # may not have Graph permissions — Azure AD would refuse the token.
        # In that case we fall through: GraphServiceClient is still created (lazy auth)
        # and the downstream try/except in setup_graph_and_licenses handles the failure.
        token_acquired = False
        try:
            credential.get_token('https://graph.microsoft.com/.default')
            token_acquired = True
        except Exception:
            if not silent:
                print(f"[{get_timestamp()}] ⚠️  Graph token not available for this app (may lack Graph API permissions)")
                import sys
                sys.stdout.flush()
        
        if token_acquired and not silent:
            print(f"[{get_timestamp()}] ✅ Authenticated successfully")
            import sys
            sys.stdout.flush()
        
        # For interactive with per-stream apps: use .default (admin pre-granted consent)
        scopes = ['https://graph.microsoft.com/.default']
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=scopes
        )
        
        _graph_clients[client_id] = graph_client
        
        return graph_client
```

**What changed:** Added `credential.get_token(...)` wrapped in try/except BEFORE creating GraphServiceClient. This ensures:
- Streams WITH Graph permissions (1, 2, 3): device code prompt appears immediately, token cached, "Authenticated" prints after real auth, no double prompt
- Stream 4 WITHOUT Graph permissions: get_token fails gracefully, warns user, falls through to lazy GraphServiceClient — downstream try/except in setup_graph_and_licenses handles the 403

---

## FILE 2: INTERACTIVE-AUTH-GUIDELINES.md

### CHANGE 2A: Update Stream 4 manual setup — add Organization.Read.All Graph permission

**BEFORE (Stream 4 section in Option B manual setup):**
```markdown
**Stream 4** — `Readiness - Power Platform` · Role: `Power Platform Administrator` · Save as `CLIENT_ID_STREAM4`

Power Platform API (`https://api.bap.microsoft.com`) → Delegated: `user_impersonation`

> Power Platform data is mainly collected via PowerShell subprocess.
```

**AFTER:**
```markdown
**Stream 4** — `Readiness - Power Platform` · Role: `Power Platform Administrator` · Save as `CLIENT_ID_STREAM4`

- Microsoft Graph → Delegated: `Organization.Read.All`
- Power Platform API (`https://api.bap.microsoft.com`) → Delegated: `user_impersonation`

> Power Platform data is collected via PowerShell subprocess (`Connect-AzAccount`). The Graph `Organization.Read.All` permission is required for license queries (`subscribed_skus`) that all streams need.
```

**What changed:** Added `Organization.Read.All` Graph delegated permission to Stream 4.

---

## FILE NOT CHANGED: setup-interactive-auth.ps1

### NOTE: Manual admin action required

The setup script currently registers Stream 4 with ONLY Power Platform API permission:
```powershell
$stream4PowerPlatformPermissions = @(
    @{ Id = "8578e004-a5c6-46e7-913e-12f58912df43"; Name = "user_impersonation" }
)
```

To add `Organization.Read.All` to Stream 4, the admin must EITHER:
1. **Azure Portal → App registrations → "Readiness - Power Platform" → API permissions → Add permission → Microsoft Graph → Delegated → Organization.Read.All → Grant admin consent**
2. OR update `setup-interactive-auth.ps1` to include Graph permissions for Stream 4 (user has forbidden agent from editing this file)

Graph `Organization.Read.All` permission ID: `498476ce-e0fe-48b0-b801-37ba7e2685c6`

---

## SUMMARY

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 1A | Core/get_graph_client.py | Force eager `credential.get_token()` before returning | Eliminates double device-code prompt; "Authenticated" prints only after real auth |
| 2A | INTERACTIVE-AUTH-GUIDELINES.md | Added `Organization.Read.All` to Stream 4 manual setup | Stream 4 needs Graph permission for license queries |
| N/A | setup-interactive-auth.ps1 | NOT CHANGED — manual admin action documented | Agent cannot edit this file per user rule |

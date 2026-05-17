# CHANGE LOG — Purview Auth Consolidation: Option B (5 → 2 Device Codes)

**Date:** 2026-05-14  
**Status:** ROLLBACK MASTER — Option A replaced by Option B  
**Scope:** Purview stream only (`--services Purview`)  
**Goal:** Consolidate 5 device-code prompts into 2 by acquiring Graph token in Python via MSAL,
then letting PowerShell handle EXO/IPPS via native `-Device` flow (proven working, no permission gaps).

**Why Option B over A:** Option A tried to acquire EXO + IPPS tokens from Python using CLIENT_ID_STREAM3,
but that app only has Graph permissions — MSAL cannot get EXO/IPPS tokens for it. Option B keeps
EXO/IPPS in PowerShell (which uses Microsoft's first-party app IDs internally), achieving 2 prompts
with zero app-registration changes.

**Result:** Device code #1 = Python MSAL (Graph), Device code #2 = PS Connect-ExchangeOnline -Device (IPPS may auto-connect).

---

## FILES TO BE CHANGED

### File 1: `Core/get_graph_client.py`

**What changes:**
1. Simplify `acquire_purview_tokens()` to Graph-only (remove EXO/IPPS token acquisition)
2. Remove unused `_EXO_SCOPE` and `_IPPS_SCOPE` constants
3. Return dict with `'graph'` key only
4. `_StaticTokenCredential` logic stays as-is (already correct)

**Why:** Stream 3 app only has Graph permissions. EXO/IPPS will be handled by PS modules using
their own first-party app IDs. The Graph token is still acquired via MSAL to feed `_StaticTokenCredential`,
eliminating the redundant DeviceCodeCredential prompt from `get_graph_client()`.

#### CURRENT CODE (Option A — lines 95-190):
```python
# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE DEVICE-CODE TOKEN ACQUISITION FOR PURVIEW STREAM
# Acquires Graph + EXO + IPPS tokens from ONE device-code prompt using MSAL's
# cached refresh token for silent follow-up scope requests.
# ═══════════════════════════════════════════════════════════════════════════════

# Module-level cache for Purview tokens (populated once, consumed by PS subprocess)
_purview_tokens = {}  # {'graph': str, 'exo': str, 'ipps': str}

_EXO_SCOPE = ['https://outlook.office365.com/.default']
_IPPS_SCOPE = ['https://ps.compliance.protection.outlook.com/.default']
_GRAPH_SCOPE = ['https://graph.microsoft.com/.default']


def acquire_purview_tokens(tenant_id, client_id):
    """Acquire Graph, EXO, and IPPS tokens via a single device-code flow.

    Uses MSAL PublicClientApplication directly (not azure-identity) so we can
    control the token cache and silently acquire EXO/IPPS tokens after the
    initial device-code authentication for Graph.

    Args:
        tenant_id: Azure AD tenant ID
        client_id: App registration client ID (CLIENT_ID_STREAM3)

    Returns:
        dict with keys 'graph', 'exo', 'ipps' — each an access token string.
        Raises RuntimeError on failure.
    """
    global _purview_tokens
    if _purview_tokens:
        return _purview_tokens

    import sys
    from .spinner import get_timestamp

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(client_id, authority=authority)

    # Step 1: Device-code flow for Graph scope — this is the ONLY user prompt
    flow = app.initiate_device_flow(scopes=_GRAPH_SCOPE)
    if 'user_code' not in flow:
        raise RuntimeError(f"Failed to initiate device code flow: {flow.get('error_description', 'unknown error')}")

    print(f"\n{'=' * 70}")
    print(f"  To sign in, open a browser and go to:  {flow['verification_uri']}")
    print(f"  Enter the code:  {flow['user_code']}")
    print(f"{'=' * 70}\n")
    sys.stdout.flush()

    graph_result = app.acquire_token_by_device_flow(flow)
    if 'access_token' not in graph_result:
        raise RuntimeError(f"Graph token acquisition failed: {graph_result.get('error_description', 'unknown error')}")

    print(f"[{get_timestamp()}] ✅ Authenticated (Graph scope)")
    sys.stdout.flush()

    # Step 2: Silent acquisition for EXO scope (uses cached refresh token — NO prompt)
    accounts = app.get_accounts()
    if not accounts:
        raise RuntimeError("No cached account after device-code auth")

    exo_result = app.acquire_token_silent(scopes=_EXO_SCOPE, account=accounts[0])
    if not exo_result or 'access_token' not in exo_result:
        # Fallback: interactive if silent fails (should not happen with correct permissions)
        exo_result = app.acquire_token_by_device_flow(app.initiate_device_flow(scopes=_EXO_SCOPE))
        if 'access_token' not in exo_result:
            raise RuntimeError(f"EXO token acquisition failed: {exo_result.get('error_description', 'unknown error')}")
    print(f"[{get_timestamp()}] ✅ EXO token acquired (silent)")
    sys.stdout.flush()

    # Step 3: Silent acquisition for IPPS scope (uses cached refresh token — NO prompt)
    ipps_result = app.acquire_token_silent(scopes=_IPPS_SCOPE, account=accounts[0])
    if not ipps_result or 'access_token' not in ipps_result:
        ipps_result = app.acquire_token_by_device_flow(app.initiate_device_flow(scopes=_IPPS_SCOPE))
        if 'access_token' not in ipps_result:
            raise RuntimeError(f"IPPS token acquisition failed: {ipps_result.get('error_description', 'unknown error')}")
    print(f"[{get_timestamp()}] ✅ IPPS token acquired (silent)")
    sys.stdout.flush()

    _purview_tokens = {
        'graph': graph_result['access_token'],
        'exo': exo_result['access_token'],
        'ipps': ipps_result['access_token'],
    }
    return _purview_tokens
```

#### NEW CODE (Option B — Graph-only):
```python
# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE DEVICE-CODE TOKEN ACQUISITION FOR PURVIEW STREAM (Graph only)
# Acquires Graph token via MSAL device-code flow so _StaticTokenCredential
# can provide it to get_graph_client() without a second DeviceCodeCredential.
# EXO/IPPS tokens are handled by PowerShell modules (first-party app IDs).
# ═══════════════════════════════════════════════════════════════════════════════

# Module-level cache for Purview Graph token (populated once, consumed by _StaticTokenCredential)
_purview_tokens = {}  # {'graph': str}

_GRAPH_SCOPE = ['https://graph.microsoft.com/.default']


def acquire_purview_tokens(tenant_id, client_id):
    """Acquire Graph token via a single device-code flow for Purview stream.

    Uses MSAL PublicClientApplication directly (not azure-identity) so the
    token can be shared with _StaticTokenCredential in get_graph_client(),
    eliminating the redundant DeviceCodeCredential prompt.

    EXO/IPPS tokens are NOT acquired here — PowerShell modules handle those
    using Microsoft's first-party app IDs (proven working, no permission gaps).

    Args:
        tenant_id: Azure AD tenant ID
        client_id: App registration client ID (CLIENT_ID_STREAM3)

    Returns:
        dict with key 'graph' — the access token string.
        Raises RuntimeError on failure.
    """
    global _purview_tokens
    if _purview_tokens:
        return _purview_tokens

    import sys
    from .spinner import get_timestamp

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(client_id, authority=authority)

    # Device-code flow for Graph scope — the ONLY Python-side user prompt
    flow = app.initiate_device_flow(scopes=_GRAPH_SCOPE)
    if 'user_code' not in flow:
        raise RuntimeError(f"Failed to initiate device code flow: {flow.get('error_description', 'unknown error')}")

    print(f"\n{'=' * 70}")
    print(f"  To sign in, open a browser and go to:  {flow['verification_uri']}")
    print(f"  Enter the code:  {flow['user_code']}")
    print(f"{'=' * 70}\n")
    sys.stdout.flush()

    graph_result = app.acquire_token_by_device_flow(flow)
    if 'access_token' not in graph_result:
        raise RuntimeError(f"Graph token acquisition failed: {graph_result.get('error_description', 'unknown error')}")

    print(f"[{get_timestamp()}] ✅ Authenticated (Graph scope)")
    sys.stdout.flush()

    _purview_tokens = {
        'graph': graph_result['access_token'],
    }
    return _purview_tokens
```

#### `_StaticTokenCredential` block (lines ~230-245) — NO CHANGE NEEDED
The existing check `if _purview_tokens.get('graph') and os.getenv('CLIENT_ID_STREAM3') == client_id`
works correctly with the simplified `_purview_tokens` dict (still has 'graph' key).

---

### File 2: `Core/orchestrator_powershell.py`

**What changes:**
1. Remove EXO/IPPS token acquisition — only get Graph token (for `_StaticTokenCredential`)
2. Remove `-ExoToken`/`-IppsToken` command-line argument passing to PS
3. Revert spinner/stdout/stderr to original PS device-code-aware behavior

**Why:** EXO/IPPS auth moves back to PowerShell's native `-Device` flow.

#### CURRENT CODE (Option A — function start, lines ~140-195):
```python
async def collect_purview_data_via_powershell():
    """Launch PowerShell to collect Purview data using pre-acquired tokens.
    
    Tokens are acquired once in Python (single device code) and passed to
    PowerShell via command-line arguments.  PowerShell uses -AccessToken
    instead of -Device, so zero device-code prompts appear in PS.
    
    Sets environment variables that will be consumed by get_purview_client.
    
    Returns:
        bool: True if data collection succeeded, False otherwise
    """
    use_device_code = os.environ.get('USE_DEVICE_CODE') == '1'
    
    # Acquire all tokens in Python via single device code (if device_code mode)
    exo_token = None
    ipps_token = None
    if use_device_code:
        try:
            from .get_graph_client import acquire_purview_tokens
            tenant_id = os.environ.get('TENANT_ID')
            client_id = os.environ.get('CLIENT_ID_STREAM3')
            tokens = acquire_purview_tokens(tenant_id, client_id)
            exo_token = tokens['exo']
            ipps_token = tokens['ipps']
        except Exception as e:
            with _stdout_lock:
                sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Token pre-acquisition failed: {e}\n')
                sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Falling back to PowerShell device-code auth\n')
                sys.stdout.flush()
    
    with _stdout_lock:
        sys.stdout.write(f'[{get_timestamp()}]   ℹ️  Launching PowerShell to collect Purview data...\n')
        if not exo_token and use_device_code:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Device code prompts will appear for Exchange Online, then Security & Compliance\n')
        elif not use_device_code:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Browser authentication windows will appear\n')
        sys.stdout.flush()
    
    # Build command line — pass tokens if available
    ps_script = os.path.join(os.path.dirname(__file__), '..', 'collect_purview_data.ps1')
    cmd = ['pwsh', '-ExecutionPolicy', 'Bypass', '-File', ps_script, '-DataOnly']
    if exo_token and ipps_token:
        cmd.extend(['-ExoToken', exo_token, '-IppsToken', ipps_token])
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1  # Line buffered
    )
```

#### NEW CODE (Option B — function start):
```python
async def collect_purview_data_via_powershell():
    """Launch PowerShell to collect Purview data with interactive authentication.
    
    Graph token is pre-acquired via MSAL (single device code) to feed
    _StaticTokenCredential in get_graph_client(). EXO/IPPS authentication
    is handled by PowerShell modules using native -Device flow.
    
    Sets environment variables that will be consumed by get_purview_client.
    
    Returns:
        bool: True if data collection succeeded, False otherwise
    """
    use_device_code = os.environ.get('USE_DEVICE_CODE') == '1'
    
    # Pre-acquire Graph token via MSAL (populates _purview_tokens for _StaticTokenCredential)
    if use_device_code:
        try:
            from .get_graph_client import acquire_purview_tokens
            tenant_id = os.environ.get('TENANT_ID')
            client_id = os.environ.get('CLIENT_ID_STREAM3')
            acquire_purview_tokens(tenant_id, client_id)
        except Exception as e:
            with _stdout_lock:
                sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Graph token pre-acquisition failed: {e}\n')
                sys.stdout.flush()
    
    with _stdout_lock:
        sys.stdout.write(f'[{get_timestamp()}]   ℹ️  Launching PowerShell to collect Purview data...\n')
        if use_device_code:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Device code prompt will appear for Exchange Online authentication\n')
        else:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Browser authentication windows will appear\n')
        sys.stdout.flush()
    
    # Launch PowerShell — no token args, PS handles EXO/IPPS auth natively
    ps_script = os.path.join(os.path.dirname(__file__), '..', 'collect_purview_data.ps1')
    cmd = ['pwsh', '-ExecutionPolicy', 'Bypass', '-File', ps_script, '-DataOnly']
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1  # Line buffered
    )
```

#### CURRENT CODE (Option A — spinner start + stdout thread, lines ~230-255):
```python
    # Start spinner — if tokens pre-acquired, auth is already done
    if exo_token and ipps_token:
        start_spinner('Collecting Purview compliance data...')
    else:
        start_spinner('Waiting for Exchange Online authentication...')
    
    # Shared buffer for stdout lines (threaded reader fills it, main thread extracts JSON later)
    stdout_lines = []
    
    # Stream stdout — device-code detection only needed if tokens were NOT pre-acquired
    def stream_stdout():
        try:
            for line in process.stdout:
                stripped = line.rstrip()
                stdout_lines.append(stripped)
                if not exo_token:
                    # Fallback mode: display device code prompts from PS
                    lower = stripped.lower()
                    if stripped and ('devicelogin' in lower or 'enter the code' in lower or 'microsoft.com/device' in lower):
                        stop_spinner()
                        with _stdout_lock:
                            sys.stdout.write(f'\n{stripped}\n\n')
                            sys.stdout.flush()
        except ValueError:
            pass
```

#### NEW CODE (Option B — spinner start + stdout thread):
```python
    # Start spinner for EXO authentication (PS will show device code via stdout)
    start_spinner('Waiting for Exchange Online authentication...')
    
    # Shared buffer for stdout lines (threaded reader fills it, main thread extracts JSON later)
    stdout_lines = []
    
    # Stream stdout in real-time — device code prompts from MSAL go to stdout via Console.WriteLine
    def stream_stdout():
        try:
            for line in process.stdout:
                stripped = line.rstrip()
                stdout_lines.append(stripped)
                # Display device code prompts in real-time
                lower = stripped.lower()
                if stripped and ('devicelogin' in lower or 'enter the code' in lower or 'microsoft.com/device' in lower):
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'\n{stripped}\n\n')
                        sys.stdout.flush()
        except ValueError:
            pass
```

#### CURRENT CODE (Option A — stderr AUTH_COMPLETE handler, lines ~258-280):
```python
                if line.startswith('AUTH_COMPLETE:'):
                    service = line.split(':', 1)[1]
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ✅ {service} connected\n')
                        if 'Exchange Online' in service and not ipps_token:
                            # Only prompt for SCC auth if tokens weren't pre-acquired
                            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Please provide credentials for Security & Compliance authentication...\n')
                            sys.stdout.flush()
                            start_spinner('Waiting for Security & Compliance authentication...')
                        else:
                            sys.stdout.flush()
                            start_spinner('Collecting Purview compliance data...')
```

#### NEW CODE (Option B — stderr AUTH_COMPLETE handler):
```python
                if line.startswith('AUTH_COMPLETE:'):
                    service = line.split(':', 1)[1]
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ✅ {service} connected\n')
                        if 'Exchange Online' in service:
                            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Please provide credentials for Security & Compliance authentication...\n')
                            sys.stdout.flush()
                            start_spinner('Waiting for Security & Compliance authentication...')
                        else:
                            sys.stdout.flush()
                            start_spinner('Collecting Purview compliance data...')
```

---

### File 3: `collect_purview_data.ps1`

**What changes:**
1. Remove `-ExoToken` and `-IppsToken` parameters
2. Remove `if ($ExoToken -ne "")` branch for EXO
3. Remove `if ($IppsToken -ne "")` branch for IPPS
4. Keep the stray `python main.py` removal (existing bug fix from Option A)

**Why:** No tokens passed from Python anymore — PS uses native `-Device` / browser auth.

#### CURRENT CODE (Option A — param block, lines 1-9):
```powershell
# PowerShell data collector for Purview compliance endpoints
# Collects deployment data via Security & Compliance cmdlets and pipes to main.py
# Usage: .\collect_purview_data.ps1 [-DataOnly]

param(
    [switch]$DataOnly,            # If set, outputs JSON only (for Python subprocess invocation)
    [string]$ExoToken = "",       # Pre-acquired EXO access token (from Python MSAL)
    [string]$IppsToken = ""       # Pre-acquired IPPS access token (from Python MSAL)
)
```

#### NEW CODE (Option B — param block):
```powershell
# PowerShell data collector for Purview compliance endpoints
# Collects deployment data via Security & Compliance cmdlets and pipes to main.py
# Usage: .\collect_purview_data.ps1 [-DataOnly]

param(
    [switch]$DataOnly  # If set, outputs JSON only (for Python subprocess invocation)
)
```

#### CURRENT CODE (Option A — EXO connect, lines ~72-83):
```powershell
    if (-not $exoConnected) {
        Write-Progress "      → Connecting to Exchange Online..." -NoNewline
        if ($ExoToken -ne "") {
            # Use pre-acquired token from Python (no device code needed)
            Connect-ExchangeOnline -AccessToken $ExoToken -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
        } elseif ($env:USE_DEVICE_CODE -eq "1") {
            Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
        } else {
            Connect-ExchangeOnline -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue | Out-Null
        }
        Write-Progress " ✓" -ForegroundColor Green
        [Console]::Error.WriteLine("AUTH_COMPLETE:Exchange Online")
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Exchange Online")
    }
```

#### NEW CODE (Option B — EXO connect):
```powershell
    if (-not $exoConnected) {
        Write-Progress "      → Connecting to Exchange Online..." -NoNewline
        if ($env:USE_DEVICE_CODE -eq "1") {
            Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
        } else {
            Connect-ExchangeOnline -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue | Out-Null
        }
        Write-Progress " ✓" -ForegroundColor Green
        [Console]::Error.WriteLine("AUTH_COMPLETE:Exchange Online")
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Exchange Online")
    }
```

#### CURRENT CODE (Option A — IPPS connect, lines ~91-107):
```powershell
    if (-not $ippsConnected) {
        # Re-check if IPPS was auto-connected by ExchangeOnline session
        try {
            Get-DlpCompliancePolicy -ErrorAction Stop | Out-Null
            $ippsConnected = $true
            [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
        } catch {
            # Not auto-connected, need to connect manually
            Write-Progress "      → Connecting to Security & Compliance..." -NoNewline
            if ($IppsToken -ne "") {
                # Use pre-acquired token from Python (no device code needed)
                Connect-IPPSSession -AccessToken $IppsToken -ErrorAction Stop -WarningAction SilentlyContinue
            } elseif ($env:USE_DEVICE_CODE -eq "1") {
                Connect-IPPSSession -Device -ErrorAction Stop -WarningAction SilentlyContinue
            } else {
                Connect-IPPSSession -ErrorAction Stop -WarningAction SilentlyContinue | Out-Null
            }
            Write-Progress " ✓" -ForegroundColor Green
            [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
        }
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
    }
```

#### NEW CODE (Option B — IPPS connect):
```powershell
    if (-not $ippsConnected) {
        # Re-check if IPPS was auto-connected by ExchangeOnline session
        try {
            Get-DlpCompliancePolicy -ErrorAction Stop | Out-Null
            $ippsConnected = $true
            [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
        } catch {
            # Not auto-connected, need to connect manually
            Write-Progress "      → Connecting to Security & Compliance..." -NoNewline
            if ($env:USE_DEVICE_CODE -eq "1") {
                Connect-IPPSSession -Device -ErrorAction Stop -WarningAction SilentlyContinue
            } else {
                Connect-IPPSSession -ErrorAction Stop -WarningAction SilentlyContinue | Out-Null
            }
            Write-Progress " ✓" -ForegroundColor Green
            [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
        }
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
    }
```

#### Catch block — the stray `python main.py` removal STAYS (existing bug fix, no rollback needed)

---

### File 4: `requirements.txt` — NO CHANGE

`msal>=1.20.0` stays — still used for Graph token acquisition in `acquire_purview_tokens()`.

### File 5: `setup-interactive-auth.ps1` — NO CHANGE

No app permission changes needed for Option B.

---

## AUTHENTICATION FLOW — BEFORE vs AFTER

### BEFORE (Option A — BROKEN, 2+ prompts with hang):
1. Python `DeviceCodeCredential` → Graph token (device code #1) — from get_graph_client() because _purview_tokens empty
2. Python MSAL `acquire_token_by_device_flow()` → Graph token (device code #2) — redundant!
3. Python MSAL `acquire_token_silent()` → EXO → FAILS (no permission) → fallback hangs

### AFTER (Option B — 2 prompts, working):
1. Python MSAL `acquire_purview_tokens()` → Graph token (device code #1) — feeds _StaticTokenCredential
2. `get_graph_client()` → uses _StaticTokenCredential (NO prompt)
3. PS `Connect-ExchangeOnline -Device` → EXO token (device code #2, first-party app ID)
4. PS `Connect-IPPSSession -Device` → may auto-connect from EXO session OR show device code #3

---

## ROLLBACK PLAN

To rollback Option B to the state BEFORE any Purview auth consolidation:

### File 1 — `Core/get_graph_client.py`:
- Remove `import msal` (line 3)
- Remove entire block from `# ═══ SINGLE DEVICE-CODE...` through `return _purview_tokens` (~lines 95-155)
- Remove `_StaticTokenCredential` conditional in `get_graph_client()` (~lines 230-244), replace with:
  ```python
          if client_id not in _credentials:
              _credentials[client_id] = _create_interactive_credential(tenant_id, client_id)
  ```

### File 2 — `Core/orchestrator_powershell.py`:
- Replace Option B function start with the original (see log CHANGE-ACTIVITY-START-20260514-FIX-PS-DEVICE-CODE-VISIBILITY-END-PENDING.md)

### File 3 — `collect_purview_data.ps1`:
- Re-add `-ExoToken`/`-IppsToken` params if rolling back to Option A
- Or remove them entirely if rolling back to pre-consolidation state

### File 4 — `requirements.txt`:
- Remove `msal>=1.20.0` line

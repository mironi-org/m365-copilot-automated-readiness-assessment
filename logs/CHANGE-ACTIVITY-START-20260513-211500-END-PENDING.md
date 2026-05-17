# CHANGE LOG — Device Code Auth Fix (Align with Old Working Codebase)
# Started: 2026-05-13 21:15:00
# Goal: Make --auth-mode device_code internally map to AUTH_MODE=interactive + USE_DEVICE_CODE=1
#        Restore _SECONDARY_SCOPES, _create_interactive_credential(), prewarm_credentials()
#        Remove forced get_token() at credential creation
#        Match the old working codebase architecture

---

## FILE 1: Core/cli_parser.py

### CHANGE 1A: After parsing, map device_code → interactive + USE_DEVICE_CODE=1

**BEFORE (lines 67-76):**
```python
    args = parser.parse_args()
    
    # If --auth-mode not provided on CLI, check AUTH_MODE env var
    if args.auth_mode is None:
        import os
        args.auth_mode = os.environ.get('AUTH_MODE', 'service_principal')
    
    # Set AUTH_MODE in environment for downstream modules
    import os
    os.environ['AUTH_MODE'] = args.auth_mode
    
    return args
```

**AFTER:**
```python
    args = parser.parse_args()
    
    # If --auth-mode not provided on CLI, check AUTH_MODE env var
    if args.auth_mode is None:
        import os
        args.auth_mode = os.environ.get('AUTH_MODE', 'service_principal')
    
    # Device code is a variant of interactive auth — map it internally
    # so all downstream code only checks AUTH_MODE == 'interactive'
    import os
    if args.auth_mode == 'device_code':
        os.environ['AUTH_MODE'] = 'interactive'
        os.environ['USE_DEVICE_CODE'] = '1'
    else:
        os.environ['AUTH_MODE'] = args.auth_mode
    
    return args
```

---

## FILE 2: Core/get_graph_client.py

### CHANGE 2A: Restore _SECONDARY_SCOPES dict (after STREAM_CLIENT_ID_MAP, before _load_env)

**BEFORE (lines 25-28):**
```python
    'A365':            'CLIENT_ID_STREAM5',
}

# Load .env file into environment variables (no external dependency)
```

**AFTER:**
```python
    'A365':            'CLIENT_ID_STREAM5',
}

# Secondary API scopes each service needs beyond https://graph.microsoft.com/.default.
# Pre-warming these after the initial Graph auth lets MSAL use the cached refresh token
# to silently acquire them — avoiding extra device-code prompts during asyncio.gather.
_SECONDARY_SCOPES = {
    'Defender':       ['https://api.securitycenter.microsoft.com/.default'],
    'Power Platform': ['https://api.bap.microsoft.com/.default',
                       'https://service.flow.microsoft.com/.default'],
    'Copilot Studio': ['https://api.bap.microsoft.com/.default',
                       'https://service.flow.microsoft.com/.default'],
}

# Load .env file into environment variables (no external dependency)
```

### CHANGE 2B: Simplify cache dicts — key by client_id only (not auth_mode tuple)

**BEFORE (lines 49-56):**
```python
# Module-level cache: per auth_mode + client_id credential and graph client
_credentials = {}   # {(auth_mode, client_id): TokenCredential}
_graph_clients = {} # {(auth_mode, client_id): GraphServiceClient}

# Legacy single-credential cache (service principal mode)
_graph_client = None
_credential = None


def _get_cache_key(auth_mode, client_id):
    return (auth_mode, client_id)
```

**AFTER:**
```python
# Module-level cache: per client_id credential and graph client
_credentials = {}   # {client_id: credential}
_graph_clients = {} # {client_id: GraphServiceClient}

# Legacy single-credential cache (service principal mode)
_graph_client = None
_credential = None
```

### CHANGE 2C: Replace _device_code_prompt_callback with old-style + add _create_interactive_credential factory

**BEFORE (lines 59-82):**
```python
def _device_code_prompt_callback(device_code_info):
    """Show device-code instructions in terminal for delegated login.
    
    Azure SDK passes a DeviceCodeInfo object with .verification_uri and .user_code attributes.
    """
    from .spinner import get_timestamp
    verification_uri = getattr(device_code_info, 'verification_uri', 'https://microsoft.com/devicelogin')
    user_code = getattr(device_code_info, 'user_code', '(code unavailable)')
    print()
    print(f"[{get_timestamp()}] ============================================================")
    print(f"[{get_timestamp()}]  DEVICE CODE AUTHENTICATION")
    print(f"[{get_timestamp()}] ============================================================")
    print(f"[{get_timestamp()}]  1. Open a browser and go to: {verification_uri}")
    print(f"[{get_timestamp()}]  2. Enter the code:           {user_code}")
    print(f"[{get_timestamp()}]  3. Sign in with your Microsoft account")
    print(f"[{get_timestamp()}] ============================================================")
    print(f"[{get_timestamp()}]  Waiting for you to complete sign-in...")
    print()
    import sys
    sys.stdout.flush()
```

**AFTER:**
```python
def _device_code_prompt(verification_uri, user_code, expires_on):
    """Callback that prints the device code login instructions to stdout."""
    import sys
    print(f"\n{'=' * 70}")
    print(f"  To sign in, open a browser and go to:  {verification_uri}")
    print(f"  Enter the code:  {user_code}")
    print(f"{'=' * 70}\n")
    sys.stdout.flush()


def _create_interactive_credential(tenant_id, client_id):
    """Create the appropriate interactive credential based on USE_DEVICE_CODE env var.
    
    In interactive mode with per-stream apps: each stream's app has its own credential,
    cached by client_id. Same stream won't prompt twice, different streams will each
    require one auth (assuming admin consent is pre-granted for all app permissions).
    """
    if os.getenv('USE_DEVICE_CODE') == '1':
        # Per-stream device code credential
        # (each stream's app has only its own permissions, pre-consented by admin)
        return DeviceCodeCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            prompt_callback=_device_code_prompt
        )
    return InteractiveBrowserCredential(
        tenant_id=tenant_id,
        client_id=client_id
    )
```

### CHANGE 2D: Rewrite get_graph_client() interactive branch — use _create_interactive_credential, cache by client_id, no forced get_token

**BEFORE (lines 84-160 — the interactive/device_code branch):**
```python
async def get_graph_client(tenant_id=None, silent=False, services=None):
    """Get Microsoft Graph SDK client using service principal or delegated authentication.
    
    In interactive/device_code modes with per-stream apps: resolves the correct CLIENT_ID
    based on the requested services. Each stream gets its own credential + Graph client.
    
    Args:
        tenant_id: Azure tenant ID (optional, read from .env if not provided)
        silent: If True, suppress authentication messages
        services: List of service names (e.g. ['M365', 'Entra']) to resolve per-stream CLIENT_ID.
                  If None, falls back to legacy single-client behavior.
        
    Returns:
        GraphServiceClient instance
    """
    global _graph_client, _credential
    
    # Get credentials from environment
    tenant_id = tenant_id or os.getenv('TENANT_ID')
    auth_mode = os.getenv('AUTH_MODE', 'service_principal')
    
    from .spinner import get_timestamp
    
    if auth_mode in ('interactive', 'device_code'):
        # Per-stream delegated auth: resolve CLIENT_ID from services
        client_id = _resolve_interactive_client_id(services)
        cache_key = _get_cache_key(auth_mode, client_id)
        
        if not tenant_id:
            raise ValueError(
                f"Missing TENANT_ID for {auth_mode} mode. Ensure .env file contains:\n"
                "  TENANT_ID=<your-tenant-id>\n"
                f"  AUTH_MODE={auth_mode}"
            )
        
        # Check cache (per auth_mode + client_id)
        if cache_key in _graph_clients:
            return _graph_clients[cache_key]
        
        if not silent:
            if auth_mode == 'device_code':
                print(f"[{get_timestamp()}] ℹ️     Authenticating with device code...")
            else:
                print(f"[{get_timestamp()}] ℹ️     Authenticating with interactive browser login...")
            import sys
            sys.stdout.flush()
        
        if cache_key not in _credentials:
            if auth_mode == 'device_code':
                _credentials[cache_key] = DeviceCodeCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    prompt_callback=_device_code_prompt_callback
                )
                # Force immediate token acquisition to trigger device code prompt
                # (Similar to: az login --use-device-code)
                try:
                    _credentials[cache_key].get_token('https://graph.microsoft.com/.default')
                except Exception as e:
                    # Token might fail if user hasn't completed sign-in, but prompt was shown
                    pass
            else:
                _credentials[cache_key] = InteractiveBrowserCredential(
                    tenant_id=tenant_id,
                    client_id=client_id
                )
        
        credential = _credentials[cache_key]
        
        # For interactive with per-stream apps: use .default (admin pre-granted consent)
        scopes = ['https://graph.microsoft.com/.default']
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=scopes
        )
        
        _graph_clients[cache_key] = graph_client
        
        if not silent:
            print(f"[{get_timestamp()}] ✅ Authenticated successfully")
            import sys
            sys.stdout.flush()
        
        return graph_client
```

**AFTER:**
```python
async def get_graph_client(tenant_id=None, silent=False, services=None):
    """Get Microsoft Graph SDK client using service principal or interactive browser authentication.
    
    In interactive mode with per-stream apps: resolves the correct CLIENT_ID based on
    the requested services. Each stream gets its own credential + Graph client.
    
    Args:
        tenant_id: Azure tenant ID (optional, read from .env if not provided)
        silent: If True, suppress authentication messages
        services: List of service names (e.g. ['M365', 'Entra']) to resolve per-stream CLIENT_ID.
                  If None, falls back to legacy single-client behavior.
        
    Returns:
        GraphServiceClient instance
    """
    global _graph_client, _credential
    
    # Get credentials from environment
    tenant_id = tenant_id or os.getenv('TENANT_ID')
    auth_mode = os.getenv('AUTH_MODE', 'service_principal')
    
    from .spinner import get_timestamp
    
    if auth_mode == 'interactive':
        # Per-stream interactive auth: resolve CLIENT_ID from services
        client_id = _resolve_interactive_client_id(services)
        
        if not tenant_id:
            raise ValueError(
                "Missing TENANT_ID for interactive mode. Ensure .env file contains:\n"
                "  TENANT_ID=<your-tenant-id>\n"
                "  AUTH_MODE=interactive"
            )
        
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

### CHANGE 2E: Rewrite get_shared_credential() — use _create_interactive_credential, cache by client_id, no forced get_token

**BEFORE (lines 247-310):**
```python
def get_shared_credential(service_name=None):
    """Get credential for non-Graph APIs (Defender, Power Platform).
    
    In delegated modes (interactive/device_code): uses per-stream CLIENT_ID based on service_name.
    In service principal mode: uses the single CLIENT_ID/CLIENT_SECRET.
    
    Args:
        service_name: Service name to resolve per-stream CLIENT_ID (e.g. 'Defender', 'Power Platform')
        
    Returns:
        ClientSecretCredential, InteractiveBrowserCredential, or DeviceCodeCredential instance
    """
    global _credential
    
    # Get credentials from environment
    tenant_id = os.getenv('TENANT_ID')
    auth_mode = os.getenv('AUTH_MODE', 'service_principal')
    
    if auth_mode in ('interactive', 'device_code'):
        # Per-stream: resolve correct CLIENT_ID
        client_id = None
        if service_name:
            env_var = STREAM_CLIENT_ID_MAP.get(service_name)
            if env_var:
                client_id = os.getenv(env_var)
        client_id = client_id or os.getenv('CLIENT_ID')
        cache_key = _get_cache_key(auth_mode, client_id)
        
        if not client_id:
            raise ValueError(
                f"No CLIENT_ID configured for {auth_mode} mode (service: {service_name}).\n"
                "Run setup-interactive-auth.ps1 to create per-stream app registrations."
            )
        
        if not tenant_id:
            raise ValueError(f"Missing TENANT_ID in .env file for {auth_mode} mode.")
        
        # Return cached credential if same auth_mode + client_id already created
        if cache_key in _credentials:
            return _credentials[cache_key]
        
        if auth_mode == 'device_code':
            cred = DeviceCodeCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                prompt_callback=_device_code_prompt_callback
            )
            # Force immediate token acquisition to trigger device code prompt
            # (Similar to: az login --use-device-code)
            try:
                cred.get_token('https://graph.microsoft.com/.default')
            except Exception as e:
                # Token might fail if user hasn't completed sign-in, but prompt was shown
                pass
        else:
            cred = InteractiveBrowserCredential(
                tenant_id=tenant_id,
                client_id=client_id
            )
        _credentials[cache_key] = cred
        return cred
```

**AFTER:**
```python
def get_shared_credential(service_name=None):
    """Get credential for non-Graph APIs (Defender, Power Platform).
    
    In interactive mode: uses per-stream CLIENT_ID based on service_name.
    In service principal mode: uses the single CLIENT_ID/CLIENT_SECRET.
    
    Args:
        service_name: Service name to resolve per-stream CLIENT_ID (e.g. 'Defender', 'Power Platform')
        
    Returns:
        ClientSecretCredential or InteractiveBrowserCredential instance
    """
    global _credential
    
    # Get credentials from environment
    tenant_id = os.getenv('TENANT_ID')
    auth_mode = os.getenv('AUTH_MODE', 'service_principal')
    
    if auth_mode == 'interactive':
        # Per-stream: resolve correct CLIENT_ID
        client_id = None
        if service_name:
            env_var = STREAM_CLIENT_ID_MAP.get(service_name)
            if env_var:
                client_id = os.getenv(env_var)
        client_id = client_id or os.getenv('CLIENT_ID')
        
        if not client_id:
            raise ValueError(
                f"No CLIENT_ID configured for interactive mode (service: {service_name}).\n"
                "Run setup-interactive-auth.ps1 to create per-stream app registrations."
            )
        
        if not tenant_id:
            raise ValueError("Missing TENANT_ID in .env file for interactive mode.")
        
        # Return cached credential if same client_id already created
        if client_id in _credentials:
            return _credentials[client_id]
        
        cred = _create_interactive_credential(tenant_id, client_id)
        _credentials[client_id] = cred
        return cred
```

### CHANGE 2F: Add prewarm_credentials() function (after get_power_platform_credential, before get_api_client)

**BEFORE:**
```python
def get_power_platform_credential():
    ...
    return get_shared_credential(service_name='Power Platform')

async def get_api_client(service_name):
```

**AFTER:**
```python
def get_power_platform_credential():
    ...
    return get_shared_credential(service_name='Power Platform')


def prewarm_credentials(services=None):
    """Pre-warm the MSAL token cache for secondary API scopes.

    Must be called AFTER the initial Graph authentication has completed (i.e., after
    setup_graph_and_licenses), so MSAL can use the cached refresh token to silently
    acquire tokens for secondary APIs (Defender, Power Platform, etc.).

    Args:
        services: List of service names being run (e.g. ['Defender', 'M365']).
    """
    if not services:
        return

    auth_mode = os.getenv('AUTH_MODE', 'service_principal')
    if auth_mode != 'interactive':
        return  # Service-principal credentials don't need pre-warming

    seen = set()  # (client_id, scope) pairs already attempted
    for service in services:
        client_id_env = STREAM_CLIENT_ID_MAP.get(service)
        if not client_id_env:
            continue
        client_id = os.getenv(client_id_env)
        if not client_id or client_id not in _credentials:
            continue  # Credential not yet created — Graph auth hasn't run for this stream

        credential = _credentials[client_id]
        for scope in _SECONDARY_SCOPES.get(service, []):
            key = (client_id, scope)
            if key in seen:
                continue
            seen.add(key)
            try:
                credential.get_token(scope)
            except Exception:
                pass  # Silent failure is handled when the pipeline actually needs the token


async def get_api_client(service_name):
```

---

## FILE 3: Core/orchestrator.py

### CHANGE 3A: Import prewarm_credentials and call it after setup_graph_and_licenses

**BEFORE (lines 10-11):**
```python
from .orchestrator_powershell import collect_power_platform_data
from .orchestrator_pipelines import create_pipelines
```

**AFTER:**
```python
from .orchestrator_powershell import collect_power_platform_data
from .orchestrator_pipelines import create_pipelines
from .get_graph_client import prewarm_credentials
```

**BEFORE (lines 68-72):**
```python
            # Initialize Graph client and licenses
            client, services_and_licenses, has_license_data = await setup_graph_and_licenses(tenant_id, show_graph_messages, services=service_config['services'])
        else:
            client = None
            services_and_licenses = None
```

**AFTER:**
```python
            # Initialize Graph client and licenses
            client, services_and_licenses, has_license_data = await setup_graph_and_licenses(tenant_id, show_graph_messages, services=service_config['services'])

            # Pre-warm secondary API token scopes (Defender, Power Platform, etc.)
            # MUST run after Graph auth completes so MSAL has a refresh token it can
            # exchange silently for the secondary scopes.  This prevents extra device-code
            # prompts from appearing mid-collection inside asyncio.gather tasks.
            prewarm_credentials(services=service_config['services'])
        else:
            client = None
            services_and_licenses = None
```

---

## FILE 4: Core/credentials_check.py

### CHANGE 4A: Simplify check_credentials — device_code is now interactive internally

**BEFORE (lines 55-62):**
```python
    # CLIENT_ID and CLIENT_SECRET are only required for service_principal mode
    if auth_mode not in ('interactive', 'device_code'):
        if not os.environ.get('CLIENT_ID'):
            missing.append('CLIENT_ID')
        if not os.environ.get('CLIENT_SECRET'):
            missing.append('CLIENT_SECRET')
```

**AFTER:**
```python
    # CLIENT_ID and CLIENT_SECRET are only required for service_principal mode
    if auth_mode != 'interactive':
        if not os.environ.get('CLIENT_ID'):
            missing.append('CLIENT_ID')
        if not os.environ.get('CLIENT_SECRET'):
            missing.append('CLIENT_SECRET')
```

### CHANGE 4B: Simplify validate_credentials_or_exit help text

**BEFORE (lines 76-85):**
```python
        print("To use this tool, you need to configure Azure credentials:")
        print("  Option 1 (Service Principal): Run .\\setup-service-principal.ps1")
        print("  Option 2 (Interactive Browser): Set TENANT_ID + AUTH_MODE=interactive in .env")
        print("           then use: python main.py --auth-mode interactive")
        print("  Option 3 (Device Code, Assessment Only): Set TENANT_ID + AUTH_MODE=device_code in .env")
        print("           then use: python main.py --auth-mode device_code")
        print("           (Do NOT use device_code with setup-interactive-auth.ps1; assessment step only)")
```

**AFTER:**
```python
        print("To use this tool, you need to configure Azure credentials:")
        print("  Option 1 (Service Principal): Run .\\setup-service-principal.ps1")
        print("  Option 2 (Interactive Browser): Set TENANT_ID + AUTH_MODE=interactive in .env")
        print("           then use: python main.py --auth-mode interactive")
        print("  Option 3 (Device Code): python main.py --auth-mode device_code")
```

---

## SUMMARY OF ALL CHANGES

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 1A | cli_parser.py | device_code → AUTH_MODE=interactive + USE_DEVICE_CODE=1 | Old working code uses interactive internally |
| 2A | get_graph_client.py | Added _SECONDARY_SCOPES dict | Needed by prewarm_credentials |
| 2B | get_graph_client.py | Cache key simplified: client_id only (removed tuple) | Match old working code |
| 2C | get_graph_client.py | Replaced _device_code_prompt_callback with _device_code_prompt + _create_interactive_credential factory | Match old working code signature and architecture |
| 2D | get_graph_client.py | Rewrote get_graph_client() interactive branch | Use factory, no forced get_token, single code path |
| 2E | get_graph_client.py | Rewrote get_shared_credential() interactive branch | Use factory, no forced get_token, single code path |
| 2F | get_graph_client.py | Added prewarm_credentials() function | Prevents extra device-code prompts in asyncio.gather |
| 3A | orchestrator.py | Import + call prewarm_credentials after Graph auth | Pre-warm secondary tokens before parallel pipelines |
| 4A | credentials_check.py | Simplified auth_mode check | device_code is now interactive internally |
| 4B | credentials_check.py | Simplified help text | Cleaner messaging |

## FILES NOT TOUCHED
- setup-interactive-auth.ps1 — NOT TOUCHED
- .env — NOT TOUCHED
- main.py — NOT TOUCHED

---
---

# CHANGE LOG — Fix "Analyzing Features" Flooding Bug (Double Device-Code Prompt)
# Added: 2026-05-14
# Goal: Prevent GraphServiceClient from triggering a SECOND device-code prompt after
#        the eager get_token() already succeeded. The second prompt interrupts the
#        progress bar's \r overwrite mechanism, causing all updates to flood as new lines.

---

## FILE: Core/get_graph_client.py

### CHANGE 5A: Move _StaticTokenCredential to module level (was inline in Purview branch)

**BEFORE (lines 64-67):**
```python
# Module-level cache: per client_id credential and graph client
_credentials = {}   # {client_id: credential}
_graph_clients = {} # {client_id: GraphServiceClient}
```

**AFTER:**
```python
# Module-level cache: per client_id credential and graph client
_credentials = {}   # {client_id: credential}
_graph_clients = {} # {client_id: GraphServiceClient}


class _StaticTokenCredential:
    """Credential that returns a pre-acquired access token.
    
    Used to prevent the Graph SDK from triggering a second device-code prompt
    when MSAL doesn't serve the cached token (azure-identity 1.25.x / msal 1.36.x).
    """
    def __init__(self, token):
        self._token = token

    def get_token(self, *scopes, **kwargs):
        from azure.core.credentials import AccessToken
        import time
        return AccessToken(self._token, int(time.time()) + 3600)
```

---

### CHANGE 5B: Remove inline _StaticTokenCredential class from Purview branch (now uses module-level class)

**BEFORE:**
```python
            # If Purview tokens were pre-acquired via acquire_purview_tokens(),
            # use a static bearer token — no device code needed
            if _purview_tokens.get('graph') and os.getenv('CLIENT_ID_STREAM3') == client_id:
                from azure.core.credentials import AccessToken
                import time

                class _StaticTokenCredential:
                    """Credential that returns a pre-acquired access token."""
                    def __init__(self, token):
                        self._token = token
                    def get_token(self, *scopes, **kwargs):
                        return AccessToken(self._token, int(time.time()) + 3600)

                _credentials[client_id] = _StaticTokenCredential(_purview_tokens['graph'])
```

**AFTER:**
```python
            # If Purview tokens were pre-acquired via acquire_purview_tokens(),
            # use a static bearer token — no device code needed
            if _purview_tokens.get('graph') and os.getenv('CLIENT_ID_STREAM3') == client_id:
                _credentials[client_id] = _StaticTokenCredential(_purview_tokens['graph'])
```

---

### CHANGE 5C: After eager get_token() succeeds, wrap token in _StaticTokenCredential (THE KEY FIX)

**BEFORE:**
```python
        token_acquired = False
        if not silent:
            try:
                credential.get_token('https://graph.microsoft.com/.default')
                token_acquired = True
            except Exception:
                print(f"[{get_timestamp()}] ⚠️  Graph token not available for this app (may lack Graph API permissions)")
                import sys
                sys.stdout.flush()
```

**AFTER:**
```python
        token_acquired = False
        if not silent:
            try:
                token_result = credential.get_token('https://graph.microsoft.com/.default')
                token_acquired = True
                # Wrap in _StaticTokenCredential so the Graph SDK's internal
                # get_token() call re-uses this token instead of triggering a
                # second device-code prompt (MSAL caching bug workaround).
                credential = _StaticTokenCredential(token_result.token)
                _credentials[client_id] = credential
            except Exception:
                print(f"[{get_timestamp()}] ⚠️  Graph token not available for this app (may lack Graph API permissions)")
                import sys
                sys.stdout.flush()
```

---

## ROOT CAUSE EXPLANATION

When running `--services M365 Entra`:
1. `check_all_service_plans()` calls `get_graph_client(silent=False)` → eager `get_token()` triggers device code #1
2. Progress bar starts: `\r[timestamp] Analyzing Features [░░░░░░░░░░] 0%`
3. `subscribed_skus.get()` → Graph SDK internally calls `credential.get_token()` AGAIN
4. MSAL (azure-identity 1.25.x / msal 1.36.x) doesn't serve the cached token → triggers device code #2
5. The device code prompt prints multi-line output with `\n`, breaking the `\r` overwrite mechanism
6. All subsequent progress bar updates appear as NEW lines (flooding ~30+ repeated lines)

The fix wraps the already-acquired token in `_StaticTokenCredential` so the SDK's internal
`get_token()` returns instantly without touching MSAL.

---

## SUMMARY OF CHANGE 5

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 5A | get_graph_client.py | _StaticTokenCredential moved to module level | Reusable by both Purview branch and eager-token branch |
| 5B | get_graph_client.py | Removed inline class from Purview branch | Uses module-level class now |
| 5C | get_graph_client.py | Wrap token after eager get_token() succeeds | Prevents SDK from triggering second device-code prompt |

## ROLLBACK INSTRUCTIONS
To rollback Change 5, revert ONLY get_graph_client.py:
1. Remove the module-level `_StaticTokenCredential` class (lines after `_graph_clients = {}`)
2. Restore the inline class inside the Purview `if` branch (Change 5B BEFORE block)
3. Replace `token_result = credential.get_token(...)` + wrapping with simple `credential.get_token(...)` (Change 5C BEFORE block)

---
---

# CHANGE LOG — Fix Connect-IPPSSession "-Device" Parameter Error
# Added: 2026-05-14
# Goal: Connect-IPPSSession does NOT support -Device parameter (unlike Connect-ExchangeOnline).
#        After EXO authenticates via device code, the module's token cache already has
#        the user's auth context, so IPPS can connect silently without any special param.

---

## FILE: collect_purview_data.ps1

### CHANGE 6A: Remove -Device from Connect-IPPSSession call (parameter doesn't exist)

**BEFORE (lines 87-92):**
```powershell
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
```

**AFTER:**
```powershell
        } catch {
            # Not auto-connected, need to connect manually
            Write-Progress "      → Connecting to Security & Compliance..." -NoNewline
            # Note: Connect-IPPSSession does NOT support -Device.
            # After Connect-ExchangeOnline -Device succeeds, the module's token
            # cache already has the user's auth context, so IPPS connects silently.
            Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
            Write-Progress " ✓" -ForegroundColor Green
            [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
```

---

## ROOT CAUSE

`Connect-IPPSSession` (ExchangeOnlineManagement module) only supports:
- Interactive browser (default)
- `-UserPrincipalName` (prefilled UPN)
- `-AccessToken` (module 3.8.0-Preview1+)
- Certificate-based auth (CBA)

It does NOT have `-Device`. The EXO module's device code flow (`Connect-ExchangeOnline -Device`)
caches the authenticated token, which `Connect-IPPSSession` can reuse automatically.

---

## SUMMARY OF CHANGE 6

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 6A | collect_purview_data.ps1 | Removed `-Device` from IPPS, use `-ShowBanner:$false` | Parameter doesn't exist; EXO token cache provides auth |

## ROLLBACK INSTRUCTIONS
To rollback Change 6, restore the if/else block with `-Device` in collect_purview_data.ps1 (see BEFORE block above).

---

## FILE 5: Core/orchestrator_powershell.py (continued)

### CHANGE 7A: Fix spinner flooding by suppressing EXO module stderr noise

**BEFORE (stream_stderr else branch):**
```python
                else:
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   {line}\n')
                        sys.stdout.flush()
```

**AFTER:**
```python
                elif line.startswith('ERROR:'):
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ❌ {line}\n')
                        sys.stdout.flush()
                elif 'devicelogin' in line.lower() or 'enter the code' in line.lower() or 'microsoft.com/device' in line.lower():
                    # Device code URL may arrive via warning stream (stderr)
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'\n{line}\n\n')
                        sys.stdout.flush()
                # Ignore all other stderr lines (EXO/IPPS module verbose/progress noise)
                # to prevent spinner corruption during device-code auth wait
```

---

## ROOT CAUSE (Change 7)

`Connect-ExchangeOnline -Device` emits verbose/progress/warning messages to stderr while
waiting for the user to complete device-code authentication. The original `else` branch in
`stream_stderr()` was printing EVERY unrecognized stderr line, calling `stop_spinner()` before
each one. This created a race condition:

1. Spinner thread writes `\r[timestamp] ⠋ Waiting for Exchange Online authentication...` (no \n)
2. stderr thread receives EXO module noise, calls `stop_spinner()`, clears line, prints `[ts] <noise>\n`
3. Multiple rapid stderr lines cause repeated stop/print cycles, flooding the terminal
4. The visual result: "Waiting for Exchange Online auth[timestamp]" repeating on separate lines

Fix: Only process `AUTH_COMPLETE:`, `ERROR:`, and device-code URL lines from stderr.
All other stderr output (EXO module internal progress) is silently ignored.

---

## SUMMARY OF CHANGE 7

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 7A | Core/orchestrator_powershell.py | Replaced catch-all else branch with specific ERROR: and device-code URL handlers; ignore other stderr | Prevents spinner flooding from EXO module verbose output |

## ROLLBACK INSTRUCTIONS
To rollback Change 7A, restore the else branch that prints all stderr lines (see BEFORE block above).

---

### CHANGE 7B: Replace \r-based spinner animation with static status line (fixes Windows terminal flooding)

**BEFORE (lines ~187-224 inside collect_purview_data_via_powershell):**
```python
    # Spinner control
    spinner_stop_event = threading.Event()
    current_spinner_message = None
    
    def run_spinner(message):
        """Display a rotating spinner with message"""
        spinner_chars = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
        idx = 0
        while not spinner_stop_event.is_set():
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   {spinner_chars[idx]} {message}')
                sys.stdout.flush()
            idx = (idx + 1) % len(spinner_chars)
            time.sleep(0.1)
    
    spinner_thread = None
    
    def start_spinner(message):
        """Start spinner with given message"""
        nonlocal spinner_thread, current_spinner_message
        current_spinner_message = message
        spinner_stop_event.clear()
        spinner_thread = threading.Thread(target=run_spinner, args=(message,), daemon=True)
        spinner_thread.start()
    
    def stop_spinner():
        """Stop and clear spinner"""
        nonlocal spinner_thread
        if spinner_thread and spinner_thread.is_alive():
            spinner_stop_event.set()
            spinner_thread.join(timeout=0.5)
            with _stdout_lock:
                # Clear the spinner line
                sys.stdout.write('\r' + ' ' * 120 + '\r')
                sys.stdout.flush()
    
    # Start spinner — PS will handle its own device-code prompts
    start_spinner('Waiting for Exchange Online authentication...')
```

**AFTER:**
```python
    # Status message control (no animation — \r is unreliable on Windows terminals)
    def print_status(message):
        """Print a single status line (no spinner animation)"""
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ⏳ {message}\n')
            sys.stdout.flush()
    
    # Compatibility shims — other code calls start/stop_spinner
    def start_spinner(message):
        print_status(message)
    
    def stop_spinner():
        pass  # Nothing to stop — no background thread
    
    # Initial status
    print_status('Waiting for Exchange Online authentication...')
```

---

## ROOT CAUSE (Change 7B)

The `\r` (carriage return) based spinner animation writes `\r[timestamp] ⠋ message` every
0.1 seconds, expecting to overwrite the same terminal line. On Windows terminals this fails:

1. The `\r` doesn't reliably move cursor to column 0 when line wraps or console buffer scrolls
2. Each 0.1s tick renders as NEW content appended to the terminal instead of overwriting
3. Result: "Waiting for Exchange Online authenticat[timestamp]" flooding dozens of lines per second
4. The stderr/stdout reader threads compound the issue by interleaving with the spinner output

Fix: Replace the threaded spinner animation with a one-shot static status line using `\n`.
The `start_spinner()` and `stop_spinner()` functions become shims (print once / no-op) so
all existing call sites (stream_stderr AUTH_COMPLETE handler, etc.) continue to work.

---

## UPDATED SUMMARY OF CHANGE 7

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 7A | Core/orchestrator_powershell.py | Replaced catch-all else branch with specific ERROR: and device-code URL handlers; ignore other stderr | Prevents flooding from EXO module verbose stderr output |
| 7B | Core/orchestrator_powershell.py | Replaced \r-based spinner animation with static ⏳ status line | \r carriage return unreliable on Windows terminals; caused visual flooding |

## ROLLBACK INSTRUCTIONS (Change 7)
To rollback Change 7A: Restore the `else:` branch in `stream_stderr()` (see 7A BEFORE block).
To rollback Change 7B: Restore the full spinner implementation with `run_spinner()`, `threading.Event()`, `start_spinner()`, `stop_spinner()` (see 7B BEFORE block).

---

## FILE 6: collect_purview_data.ps1 (continued)

### CHANGE 8A: IPPS connection — try -Device first with fallback, handle auth failure gracefully

**BEFORE (lines 78-97):**
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
            # Note: Connect-IPPSSession does NOT support -Device.
            # After Connect-ExchangeOnline -Device succeeds, the module's token
            # cache already has the user's auth context, so IPPS connects silently.
            Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
            Write-Progress " ✓" -ForegroundColor Green
            [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
        }
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
    }
```

**AFTER:**
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
            $ippsSuccess = $false
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Try -Device first (available in EXO module 3.4.0+)
                try {
                    Connect-IPPSSession -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    if ($_.Exception.Message -like "*parameter*Device*" -or $_.Exception.Message -like "*A parameter cannot be found*") {
                        # -Device not supported in this module version, try without
                        [Console]::Error.WriteLine("IPPS_INFO: -Device not supported, trying interactive auth...")
                        try {
                            Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop
                            $ippsSuccess = $true
                        } catch {
                            [Console]::Error.WriteLine("ERROR: IPPS connection failed: $($_.Exception.Message)")
                        }
                    } else {
                        [Console]::Error.WriteLine("ERROR: IPPS connection failed: $($_.Exception.Message)")
                    }
                }
            } else {
                # Interactive/browser mode
                try {
                    Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS connection failed: $($_.Exception.Message)")
                }
            }
            if ($ippsSuccess) {
                Write-Progress " ✓" -ForegroundColor Green
                [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
            } else {
                Write-Progress " ✗ (skipped)" -ForegroundColor Yellow
                [Console]::Error.WriteLine("AUTH_SKIPPED:Security & Compliance")
            }
        }
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
    }
```

---

### CHANGE 8B: Python stream_stderr — state-based stderr passthrough + AUTH_SKIPPED handling

**BEFORE (stream_stderr in collect_purview_data_via_powershell):**
```python
    # Stream stderr in real-time to show authentication progress
    def stream_stderr():
        try:
            for line in process.stderr:
                line = line.strip()
                if not line:
                    continue
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
                elif line.startswith('ERROR:'):
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ❌ {line}\n')
                        sys.stdout.flush()
                elif 'devicelogin' in line.lower() or 'enter the code' in line.lower() or 'microsoft.com/device' in line.lower():
                    # Device code URL may arrive via warning stream (stderr)
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'\n{line}\n\n')
                        sys.stdout.flush()
                # Ignore all other stderr lines (EXO/IPPS module verbose/progress noise)
                # to prevent spinner corruption during device-code auth wait
        except ValueError:
            # Pipe closed, thread can exit
            pass
```

**AFTER:**
```python
    # Stream stderr in real-time to show authentication progress
    exo_connected = threading.Event()  # Set after EXO auth completes
    
    def stream_stderr():
        try:
            for line in process.stderr:
                line = line.strip()
```

---

## CHANGE 10A: Skip IPPS-dependent cmdlets when Security & Compliance session not established

**FILE:** collect_purview_data.ps1

**PROBLEM:** When IPPS auth is skipped (device_code mode, -Device not supported), the script still tries to run IPPS-dependent cmdlets (Get-DlpCompliancePolicy, Get-Label, etc.). These cmdlets implicitly try to re-authenticate, causing the process to hang indefinitely.

**FIX 1 — Set $ippsConnected = $true when connection succeeds (line ~107):**

**BEFORE:**
```powershell
            if ($ippsSuccess) {
                Write-Progress " ✓" -ForegroundColor Green
                [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
```

**AFTER:**
```powershell
            if ($ippsSuccess) {
                $ippsConnected = $true
                Write-Progress " ✓" -ForegroundColor Green
                [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
```

**FIX 2 — Gate all IPPS cmdlets behind $ippsConnected check (after Step 2 header):**

**BEFORE:**
```powershell
$purviewData = @{}
$permissionFailures = @()

# Collect DLP Policies
Write-Progress "      → DLP Compliance Policies..." -NoNewline
try {
    $dlpPolicies = Get-DlpCompliancePolicy -ErrorAction Stop | Select-Object ...
```

**AFTER:**
```powershell
$purviewData = @{}
$permissionFailures = @()

# Skip all IPPS-dependent cmdlets if Security & Compliance session was not established
if (-not $ippsConnected) {
    $purviewData['dlp_policies'] = @{ count = 0; policies = @(); permission_denied = $true }
    $purviewData['sensitivity_labels'] = @{ count = 0; labels = @(); permission_denied = $true }
    $purviewData['retention_policies'] = @{ count = 0; policies = @(); permission_denied = $true }
    $purviewData['label_policies'] = @{ count = 0; policies = @(); permission_denied = $true }
    $purviewData['insider_risk_policies'] = @{ count = 0; policies = @(); permission_denied = $true }
    $purviewData['communication_compliance'] = @{ count = 0; policies = @(); permission_denied = $true }
    $purviewData['information_barriers'] = @{ count = 0; policies = @(); permission_denied = $true }
    $purviewData['ediscovery_cases'] = @{ count = 0; cases = @(); permission_denied = $true }
    $permissionFailures += @("DLP Policies", "Sensitivity Labels", "Retention Policies",
        "Label Policies", "Insider Risk Policies", "Communication Compliance",
        "Information Barriers", "eDiscovery Cases")
} else {
    # ... all 8 IPPS cmdlet try/catch blocks ...
} # End of IPPS-connected cmdlets block

# EXO cmdlets (Get-OrganizationConfig, Get-IRMConfiguration, Get-AdminAuditLogConfig) remain outside
```

---

## Change 10B — Explicit `exit 0` at End of DataOnly Path

**Date/Time:** 2025-05-13 ~22:30  
**File:** `collect_purview_data.ps1`  
**Reason:** PowerShell returns exit code 1 when caught errors (e.g., failed `Connect-IPPSSession -Device`) leave `$?` as `$false`. Without explicit `exit 0`, the implicit exit code = last error state. This causes Python to think PS failed even though data was collected successfully.

**BEFORE (lines ~335-337):**
```powershell
if ($DataOnly) {
    # DataOnly mode: Output JSON to stdout (for Python subprocess)
    Write-Output $jsonData
} else {
```

**AFTER:**
```powershell
if ($DataOnly) {
    # DataOnly mode: Output JSON to stdout (for Python subprocess)
    Write-Output $jsonData
    exit 0
} else {
```

**Rollback:** Remove the `exit 0` line.

---

## Change 10C — Set `$exoConnected = $true` After Fresh EXO Connection

**Date/Time:** 2025-05-13 ~22:30  
**File:** `collect_purview_data.ps1`  
**Reason:** After `Connect-ExchangeOnline` succeeds in the `if (-not $exoConnected)` block, the variable was never set to `$true`. This is a bug — the cosmetic status message on line ~119 (`if ($ippsConnected -and $exoConnected)`) would never show correctly after a fresh connection. The variable stayed `$false` despite a successful connection.

**BEFORE (lines ~65-74):**
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
```

**AFTER:**
```powershell
    if (-not $exoConnected) {
        Write-Progress "      → Connecting to Exchange Online..." -NoNewline
        if ($env:USE_DEVICE_CODE -eq "1") {
            Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
        } else {
            Connect-ExchangeOnline -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue | Out-Null
        }
        $exoConnected = $true
        Write-Progress " ✓" -ForegroundColor Green
        [Console]::Error.WriteLine("AUTH_COMPLETE:Exchange Online")
    } else {
```

**Rollback:** Remove the `$exoConnected = $true` line after the connection commands.

---

## Change 10D — Diagnostic Improvements to Python Error Messages

**Date/Time:** 2025-05-13 ~22:30  
**Files:** `Core/orchestrator_powershell.py`, `main.py`  
**Reason:** If exit code 1 persists, we need to see: (a) the actual PS exit code value, (b) how much stdout was captured, (c) full Python traceback for any exception.

### 10D-1: `Core/orchestrator_powershell.py` — Show exit code and stdout size

**BEFORE:**
```python
    if result_returncode != 0:
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ✗ PowerShell data collection failed\n')
            sys.stdout.flush()
```

**AFTER:**
```python
    if result_returncode != 0:
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ✗ PowerShell data collection failed (exit code: {result_returncode})\n')
            sys.stdout.write(f'[{get_timestamp()}]   stdout captured: {len(stdout)} chars\n')
            sys.stdout.flush()
```

### 10D-2: `main.py` — Add traceback printing on unexpected exceptions

**BEFORE:**
```python
    except Exception as e:
        print(f"\n[{get_timestamp()}] ❌ Unexpected error: {e}")
        sys.exit(1)
```

**AFTER:**
```python
    except Exception as e:
        import traceback
        print(f"\n[{get_timestamp()}] ❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
```

**Rollback 10D-1:** Revert the f-string back to the original message without exit code/stdout info.  
**Rollback 10D-2:** Remove `import traceback` and `traceback.print_exc()` lines.

**FIX 3 — Close the else block after eDiscovery Cases (before Organization Config):**

---

## CHANGE 13A: IPPS AccessToken Auth (collect_purview_data.ps1 lines 80-117)

**Problem:** `Connect-IPPSSession` does NOT have a `-Device` parameter. The current code
tries `-Device`, fails with "parameter not found", sends ERROR+AUTH_SKIPPED, and all
8 IPPS cmdlets get skipped with `permission_denied = $true`.

**Solution:** After `Connect-ExchangeOnline -Device` succeeds, acquire an access token
for the Security & Compliance endpoint using MSAL cache, then pass it to
`Connect-IPPSSession -AccessToken $token -UserPrincipalName $upn`.

**Prerequisite:** ExchangeOnlineManagement module 3.8.0+ (confirmed: user has 3.9.2).

### BEFORE (lines 80-117, Change 9A state — CURRENT CODE):
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
            $ippsSuccess = $false
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Try -Device first (available in EXO module 3.4.0+)
                try {
                    Connect-IPPSSession -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    # -Device not supported or failed — cannot fall back to browser in piped subprocess
                    # (browser/WAM auth hangs forever when stdout/stderr are redirected)
                    [Console]::Error.WriteLine("ERROR: IPPS -Device auth failed: $($_.Exception.Message)")
                }
            } else {
                # Interactive/browser mode
                try {
                    Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS connection failed: $($_.Exception.Message)")
                }
            }
            if ($ippsSuccess) {
                $ippsConnected = $true
                Write-Progress " ✓" -ForegroundColor Green
                [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
            } else {
                Write-Progress " ✗ (skipped)" -ForegroundColor Yellow
                [Console]::Error.WriteLine("AUTH_SKIPPED:Security & Compliance")
            }
        }
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
    }
```

### AFTER (Change 13A — AccessToken approach):
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
            $ippsSuccess = $false
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Connect-IPPSSession does NOT support -Device parameter.
                # Strategy: Get an access token for the compliance endpoint via MSAL
                # using the same credentials from the EXO device-code session,
                # then pass it with -AccessToken (requires EXO module 3.8.0+).
                try {
                    # Get the UPN from the already-connected EXO session
                    $exoSession = Get-ConnectionInformation -ErrorAction Stop | Select-Object -First 1
                    $upn = $exoSession.UserPrincipalName
                    if (-not $upn) { throw "Could not determine UPN from EXO session" }

                    # Acquire token for the Security & Compliance audience
                    # The EXO module's internal MSAL cache has the refresh token from device-code auth
                    $complianceUrl = "https://ps.compliance.protection.outlook.com"
                    $tokenResult = Get-AzAccessToken -ResourceUrl $complianceUrl -ErrorAction Stop 2>$null
                    if ($tokenResult -and $tokenResult.Token) {
                        Connect-IPPSSession -AccessToken $tokenResult.Token -UserPrincipalName $upn -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                        $ippsSuccess = $true
                    } else {
                        throw "Get-AzAccessToken returned no token for compliance endpoint"
                    }
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS AccessToken auth failed: $($_.Exception.Message)")
                    # Fallback: try plain Connect-IPPSSession (may work if WAM/browser is available)
                    try {
                        Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                        $ippsSuccess = $true
                    } catch {
                        [Console]::Error.WriteLine("ERROR: IPPS fallback auth also failed: $($_.Exception.Message)")
                    }
                }
            } else {
                # Interactive/browser mode
                try {
                    Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS connection failed: $($_.Exception.Message)")
                }
            }
            if ($ippsSuccess) {
                $ippsConnected = $true
                Write-Progress " ✓" -ForegroundColor Green
                [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
            } else {
                Write-Progress " ✗ (skipped)" -ForegroundColor Yellow
                [Console]::Error.WriteLine("AUTH_SKIPPED:Security & Compliance")
            }
        }
    } else {
        [Console]::Error.WriteLine("AUTH_COMPLETE:Security & Compliance")
    }
```

### ROLLBACK:
Replace the entire AFTER block with the BEFORE block above (lines 80-117 of collect_purview_data.ps1).

---

## CHANGE 13B: IPPS MSAL Device Code Auth (replaces 13A)

**Problem:** Change 13A used `Get-AzAccessToken` which relies on Az.Accounts module's
separate authentication context — returned "UnAuthorized". The browser fallback hung
the subprocess (no browser available when stdout/stderr piped) causing 300s timeout.

**Solution:** Use MSAL.NET library (ships inside ExchangeOnlineManagement module itself)
to run an independent device code flow targeting the compliance endpoint scope
`https://ps.compliance.protection.outlook.com/.default`. This gives the user a SECOND
device code specifically for IPPS, then passes the resulting token to
`Connect-IPPSSession -AccessToken`. No external modules required.

**Key changes vs 13A:**
- Removed: `Get-AzAccessToken` (requires Az.Accounts)
- Removed: Browser fallback `Connect-IPPSSession` (hangs in piped subprocess)
- Added: Load MSAL.NET from EXO module's own directory
- Added: `AcquireTokenWithDeviceCode` targeting compliance scope
- Added: Device code message written to stderr for Python orchestrator display

### BEFORE (Change 13A state):
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Connect-IPPSSession does NOT support -Device parameter.
                # Strategy: Get an access token for the compliance endpoint via MSAL
                # using the same credentials from the EXO device-code session,
                # then pass it with -AccessToken (requires EXO module 3.8.0+).
                try {
                    # Get the UPN from the already-connected EXO session
                    $exoSession = Get-ConnectionInformation -ErrorAction Stop | Select-Object -First 1
                    $upn = $exoSession.UserPrincipalName
                    if (-not $upn) { throw "Could not determine UPN from EXO session" }

                    # Acquire token for the Security & Compliance audience
                    # The EXO module's internal MSAL cache has the refresh token from device-code auth
                    $complianceUrl = "https://ps.compliance.protection.outlook.com"
                    $tokenResult = Get-AzAccessToken -ResourceUrl $complianceUrl -ErrorAction Stop 2>$null
                    if ($tokenResult -and $tokenResult.Token) {
                        Connect-IPPSSession -AccessToken $tokenResult.Token -UserPrincipalName $upn -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                        $ippsSuccess = $true
                    } else {
                        throw "Get-AzAccessToken returned no token for compliance endpoint"
                    }
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS AccessToken auth failed: $($_.Exception.Message)")
                    # Fallback: try plain Connect-IPPSSession (may work if WAM/browser is available)
                    try {
                        Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                        $ippsSuccess = $true
                    } catch {
                        [Console]::Error.WriteLine("ERROR: IPPS fallback auth also failed: $($_.Exception.Message)")
                    }
                }
```

### AFTER (Change 13B — MSAL device code):
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Connect-IPPSSession does NOT support -Device parameter.
                # Strategy: Use MSAL.NET (shipped with EXO module) to run a device code flow
                # for the compliance endpoint, then pass the token to Connect-IPPSSession -AccessToken.
                try {
                    # Get the UPN from the already-connected EXO session
                    $exoSession = Get-ConnectionInformation -ErrorAction Stop | Select-Object -First 1
                    $upn = $exoSession.UserPrincipalName
                    if (-not $upn) { throw "Could not determine UPN from EXO session" }

                    # Load MSAL.NET from the EXO module directory
                    $msalLoaded = [System.AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.GetName().Name -eq 'Microsoft.Identity.Client' }
                    if (-not $msalLoaded) {
                        $exoModuleBase = (Get-Module ExchangeOnlineManagement).ModuleBase
                        $msalDll = Join-Path $exoModuleBase "netCore\Microsoft.Identity.Client.dll"
                        if (-not (Test-Path $msalDll)) {
                            $msalDll = Join-Path $exoModuleBase "NetFramework\Microsoft.Identity.Client.dll"
                        }
                        if (-not (Test-Path $msalDll)) { throw "Cannot find MSAL DLL in EXO module" }
                        Add-Type -Path $msalDll -ErrorAction Stop
                    }

                    # Build MSAL public client app (same registered app as EXO module)
                    $clientId = "fb78d390-0c51-40cd-8e17-fdbfab77341b"
                    $app = [Microsoft.Identity.Client.PublicClientApplicationBuilder]::Create($clientId).
                        WithAuthority("https://login.microsoftonline.com/common").
                        WithDefaultRedirectUri().
                        Build()

                    # Device code flow for compliance scope
                    $scopes = [string[]]@("https://ps.compliance.protection.outlook.com/.default")
                    $deviceCodeCallback = [System.Func[Microsoft.Identity.Client.DeviceCodeResult, System.Threading.Tasks.Task]]{
                        param($dcr)
                        # Write device code message to stderr so Python orchestrator displays it
                        [Console]::Error.WriteLine($dcr.Message)
                        return [System.Threading.Tasks.Task]::CompletedTask
                    }

                    $authResult = $app.AcquireTokenWithDeviceCode($scopes, $deviceCodeCallback).ExecuteAsync().GetAwaiter().GetResult()

                    if ($authResult -and $authResult.AccessToken) {
                        Connect-IPPSSession -AccessToken $authResult.AccessToken -UserPrincipalName $upn -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                        $ippsSuccess = $true
                    } else {
                        throw "MSAL device code flow returned no access token"
                    }
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS device-code auth failed: $($_.Exception.Message)")
                }
```

### ROLLBACK:
Replace Change 13B code with Change 13A BEFORE block (original Change 9A state).
The BEFORE block is the Change 9A state which is known to produce exit 0 (IPPS skipped but EXO works).

**BEFORE:**
```powershell
    $permissionFailures += "eDiscovery Cases"
}

# Collect Organization Configuration
```

**AFTER:**
```powershell
    $permissionFailures += "eDiscovery Cases"
}

} # End of IPPS-connected cmdlets block

# Collect Organization Configuration
```
                if not line:
                    continue
                if line.startswith('AUTH_COMPLETE:'):
                    service = line.split(':', 1)[1]
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ✅ {service} connected\n')
                        if 'Exchange Online' in service:
                            exo_connected.set()
                            sys.stdout.write(f'[{get_timestamp()}]   ⏳ Connecting to Security & Compliance...\n')
                            sys.stdout.flush()
                        else:
                            sys.stdout.flush()
                            start_spinner('Collecting Purview compliance data...')
                elif line.startswith('AUTH_SKIPPED:'):
                    service = line.split(':', 1)[1]
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ⚠️  {service} skipped (auth not available in device_code mode)\n')
                        sys.stdout.flush()
                        start_spinner('Collecting Purview compliance data (limited)...')
                elif line.startswith('ERROR:'):
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ❌ {line}\n')
                        sys.stdout.flush()
                elif 'devicelogin' in line.lower() or 'enter the code' in line.lower() or 'microsoft.com/device' in line.lower():
                    # Device code URL may arrive via warning stream (stderr)
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'\n{line}\n\n')
                        sys.stdout.flush()
                elif exo_connected.is_set():
                    # After EXO connected, show IPPS/other stderr (safe — no spinner race)
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   {line}\n')
                        sys.stdout.flush()
                # Before EXO connects: ignore stderr (EXO module verbose noise)
        except ValueError:
            # Pipe closed, thread can exit
            pass
```

---

## ROOT CAUSE (Change 8)

After EXO connects with `-Device`, `Connect-IPPSSession` was called with:
- `-ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue`

The problem: `Connect-IPPSSession` does NOT support `-Device` in the user's EXO module version.
Without `-Device`, it defaults to WAM/browser authentication which HANGS in a piped subprocess
(stdout/stderr redirected = no browser popup possible).

Fix:
1. Try `-Device` on IPPS first (works on EXO module 3.4.0+)
2. If parameter error, fall back to plain `Connect-IPPSSession` without `-WarningAction SilentlyContinue`
   (lets any auth prompt through)
3. If that also fails, send `AUTH_SKIPPED:Security & Compliance` and continue with limited data
4. Python handler shows all stderr after EXO connects (IPPS auth prompts visible to user)
5. New `AUTH_SKIPPED:` signal allows graceful degradation

---

## SUMMARY OF CHANGE 8

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 8A | collect_purview_data.ps1 | Try -Device for IPPS, fallback to plain, AUTH_SKIPPED if both fail | Prevents infinite hang on IPPS auth in device_code mode |
| 8B | Core/orchestrator_powershell.py | State-based stderr (show after EXO), AUTH_SKIPPED handler | Shows IPPS auth prompts to user; graceful degradation |

## ROLLBACK INSTRUCTIONS (Change 8)
To rollback Change 8A: Replace IPPS connection block with original single `Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue` (see 8A BEFORE block).
To rollback Change 8B: Replace `stream_stderr()` with the Change 7A version that ignores all non-signal stderr lines (see 8B BEFORE block).

---

### CHANGE 9A: Remove browser fallback for IPPS in device_code mode (prevents hang)

**Root Cause**: In device_code mode, if `Connect-IPPSSession -Device` fails (param not found), the fallback
`Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop` tries WAM/browser auth which HANGS
indefinitely in a piped subprocess (stdout/stderr redirected = no browser popup possible).
The cmdlet does NOT throw — it blocks forever.

**BEFORE (collect_purview_data.ps1 — IPPS device_code branch):**
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Try -Device first (available in EXO module 3.4.0+)
                try {
                    Connect-IPPSSession -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    if ($_.Exception.Message -like "*parameter*Device*" -or $_.Exception.Message -like "*A parameter cannot be found*") {
                        # -Device not supported in this module version, try without
                        [Console]::Error.WriteLine("IPPS_INFO: -Device not supported, trying interactive auth...")
                        try {
                            Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop
                            $ippsSuccess = $true
                        } catch {
                            [Console]::Error.WriteLine("ERROR: IPPS connection failed: $($_.Exception.Message)")
                        }
                    } else {
                        [Console]::Error.WriteLine("ERROR: IPPS connection failed: $($_.Exception.Message)")
                    }
                }
            } else {
```

**AFTER:**
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Try -Device first (available in EXO module 3.4.0+)
                try {
                    Connect-IPPSSession -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    # -Device not supported or failed — cannot fall back to browser in piped subprocess
                    # (browser/WAM auth hangs forever when stdout/stderr are redirected)
                    [Console]::Error.WriteLine("ERROR: IPPS -Device auth failed: $($_.Exception.Message)")
                }
            } else {
```

---

### CHANGE 9B: Add 5-minute timeout to process.wait() in Python (prevents indefinite hang)

**BEFORE (Core/orchestrator_powershell.py):**
```python
    # Wait for process to complete
    process.wait()
    result_returncode = process.returncode
```

**AFTER:**
```python
    # Wait for process to complete (with timeout to prevent indefinite hang)
    try:
        process.wait(timeout=300)  # 5 minute timeout
    except subprocess.TimeoutExpired:
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  PowerShell process timed out after 5 minutes — terminating\n')
            sys.stdout.flush()
        process.kill()
        process.wait()
    result_returncode = process.returncode
```

---

### CHANGE 9C: Cleared __pycache__ folders (stale .pyc was running old code)

Command: `Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force`

---

## SUMMARY OF CHANGE 9

| # | File | What Changed | Why |
|---|------|-------------|-----|
| 9A | collect_purview_data.ps1 | Removed browser fallback in device_code mode — if -Device fails, skip immediately | Browser/WAM auth hangs forever in piped subprocess |
| 9B | Core/orchestrator_powershell.py | Added 5-min timeout to process.wait() + kill on timeout | Safety net if PS still hangs for any reason |
| 9C | __pycache__/ | Cleared all .pyc cache files | Stale bytecode was running old code |

## ROLLBACK INSTRUCTIONS (Change 9)
To rollback Change 9A: Restore the nested try/catch with browser fallback (see 9A BEFORE block).
To rollback Change 9B: Replace timeout block with simple `process.wait()` (see 9B BEFORE block).
Change 9C is non-reversible (cache regenerates automatically).

---

## CHANGE 11: Fix deadlock — _stdout_lock threading.Lock → threading.RLock
**Date:** 2026-05-14 ~13:50

### Root Cause
`_stdout_lock` was `threading.Lock()` (non-reentrant). In `stream_stderr()`, the `AUTH_SKIPPED` handler called `start_spinner()` **inside** a `with _stdout_lock:` block. `start_spinner` → `print_status` tried to re-acquire the same lock → **deadlock**. This froze the stderr thread, and when `process.wait(timeout=300)` expired, the main thread also deadlocked trying to acquire `_stdout_lock` for the timeout message.

### CHANGE 11A: Core/spinner.py — Lock type change

**BEFORE:**
```python
# Global lock to prevent multiple threads from writing to stdout simultaneously
_stdout_lock = threading.Lock()
```

**AFTER:**
```python
# Global lock to prevent multiple threads from writing to stdout simultaneously
# Use RLock (reentrant) so the same thread can re-acquire without deadlocking
# (e.g. start_spinner → print_status called inside a with _stdout_lock block)
_stdout_lock = threading.RLock()
```

### Test Result
`python main.py --auth-mode device_code --services Purview` → **exit code 0** ✅
- Graph auth ✅, EXO connected ✅, IPPS skipped gracefully ✅
- Data collection completed, no hang, no deadlock

## ROLLBACK INSTRUCTIONS (Change 11)
To rollback Change 11A: Replace `threading.RLock()` with `threading.Lock()` in Core/spinner.py (line 11).

---

## CHANGE 15: IPPS MSAL Device Code via C# Helper (collect_purview_data.ps1)
**Date:** 2026-05-14 ~15:30

**Problem:** `Connect-IPPSSession` does NOT support `-Device`. The current code (Change 14A state)
uses `Connect-ExchangeOnline -Device -ConnectionUri` targeting the compliance endpoint — this
produced a 2nd device code but did NOT actually connect to IPPS (just created another EXO session).
Earlier attempts to use a PowerShell scriptblock as MSAL callback failed with "There is no Runspace
available to run scripts in this thread" (callback fires on .NET threadpool thread, no PS runspace).
The C# Add-Type approach failed with CS1701 assembly mismatch (.NET 10 runtime vs .NET 8 MSAL DLL).

**Solution:** Use `Add-Type` with `/nowarn:1701` compiler option + explicit `System.Console` assembly
reference to compile a C# helper class. The C# callback writes the device code to stderr (for Python
orchestrator to display), runs an independent MSAL device code flow for the compliance scope, then
passes the token to `Connect-IPPSSession -AccessToken`.

**Tested:** `/nowarn:1701` confirmed working — C# compiles, callback fires, device code appears on stderr.
Result: 3 device codes total (Graph + EXO + IPPS), all working.

### BEFORE (Change 14A state — lines 92-115, IPPS device_code block):
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Strategy: Reuse EXO module's in-process MSAL token cache.
                # Connect-ExchangeOnline with -Device + -ConnectionUri targeting compliance endpoint.
                # The MSAL cache already has the user's refresh token from the EXO connection,
                # so it should silently acquire a compliance token — NO additional device code prompt.
                try {
                    Connect-ExchangeOnline -Device `
                        -ConnectionUri "https://ps.compliance.protection.outlook.com/PowerShell-LiveId" `
                        -AzureADAuthorizationEndpointUri "https://login.microsoftonline.com/common" `
                        -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                    $ippsSuccess = $true
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS via EXO ConnectionUri failed: $($_.Exception.Message)")
                    # Fallback: try Connect-IPPSSession without -Device (interactive browser)
                    try {
                        Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                        $ippsSuccess = $true
                    } catch {
                        [Console]::Error.WriteLine("ERROR: IPPS fallback also failed: $($_.Exception.Message)")
                    }
                }
            } else {
```

### AFTER (Change 15 — C# MSAL device code with /nowarn:1701):
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                # Connect-IPPSSession does NOT support -Device parameter.
                # Strategy: Use MSAL.NET (shipped with EXO module) via a compiled C# helper
                # to run a device code flow for the compliance scope, then pass the token
                # to Connect-IPPSSession -AccessToken.
                # C# helper needed because PS scriptblock callbacks fail with "no Runspace" on threadpool.
                # /nowarn:1701 suppresses assembly version mismatch (.NET 10 runtime vs .NET 8 MSAL DLL).
                try {
                    $exoSession = Get-ConnectionInformation -ErrorAction Stop | Select-Object -First 1
                    $upn = $exoSession.UserPrincipalName
                    if (-not $upn) { throw "Could not determine UPN from EXO session" }

                    # Load MSAL.NET from the EXO module directory
                    $msalLoaded = [System.AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.GetName().Name -eq 'Microsoft.Identity.Client' }
                    if (-not $msalLoaded) {
                        $exoModuleBase = (Get-Module ExchangeOnlineManagement).ModuleBase
                        $msalDll = Join-Path $exoModuleBase "netCore\Microsoft.Identity.Client.dll"
                        if (-not (Test-Path $msalDll)) {
                            $msalDll = Join-Path $exoModuleBase "NetFramework\Microsoft.Identity.Client.dll"
                        }
                        if (-not (Test-Path $msalDll)) { throw "Cannot find MSAL DLL in EXO module" }
                        Add-Type -Path $msalDll -ErrorAction Stop
                    }

                    # Compile C# helper for device code callback (avoids PS runspace issue on threadpool)
                    $callbackTypeDefined = [System.AppDomain]::CurrentDomain.GetAssemblies() | ForEach-Object { try { $_.GetType('IppsDeviceCodeHelper') } catch {} } | Where-Object { $_ -ne $null }
                    if (-not $callbackTypeDefined) {
                        $helperSource = @"
using System;
using System.Threading.Tasks;
using Microsoft.Identity.Client;
public static class IppsDeviceCodeHelper {
    public static Func<DeviceCodeResult, Task> GetCallback() {
        return dcr => { Console.Error.WriteLine(dcr.Message); return Task.CompletedTask; };
    }
}
"@
                        $msalAssemblyPath = ([Microsoft.Identity.Client.PublicClientApplicationBuilder].Assembly.Location)
                        $consoleAssembly = ([System.Console].Assembly.Location)
                        Add-Type -TypeDefinition $helperSource -ReferencedAssemblies @($msalAssemblyPath, $consoleAssembly) -CompilerOptions '/nowarn:1701' -ErrorAction Stop
                    }

                    # Build MSAL public client app (same registered app as EXO module)
                    $clientId = "fb78d390-0c51-40cd-8e17-fdbfab77341b"
                    $app = [Microsoft.Identity.Client.PublicClientApplicationBuilder]::Create($clientId).
                        WithAuthority("https://login.microsoftonline.com/common").
                        WithDefaultRedirectUri().
                        Build()

                    # Device code flow for compliance scope — callback writes to stderr for Python display
                    $scopes = [string[]]@("https://ps.compliance.protection.outlook.com/.default")
                    $callback = [IppsDeviceCodeHelper]::GetCallback()
                    $authResult = $app.AcquireTokenWithDeviceCode($scopes, $callback).ExecuteAsync().GetAwaiter().GetResult()

                    if ($authResult -and $authResult.AccessToken) {
                        Connect-IPPSSession -AccessToken $authResult.AccessToken -UserPrincipalName $upn -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
                        $ippsSuccess = $true
                    } else {
                        throw "MSAL device code flow returned no access token for compliance"
                    }
                } catch {
                    [Console]::Error.WriteLine("ERROR: IPPS device-code auth failed: $($_.Exception.Message)")
                }
            } else {
```

### ROLLBACK (Change 15)
To rollback Change 15 → restore Change 14A: Replace the IPPS `if ($env:USE_DEVICE_CODE -eq "1")` block
with the BEFORE block above (Connect-ExchangeOnline -Device -ConnectionUri approach).

---

## Change 16: Add Organization.Read.All to Stream 3 (Purview)

### Root Cause
The license check in `get_purview_info.py` calls `client.subscribed_skus.get()` which hits the Graph API `/subscribedSkus` endpoint. This requires the `Organization.Read.All` delegated permission. Stream 3's app registration did not have this permission — causing HTTP 403 even when signed in as Global Admin, because the **app** itself lacked the permission scope.

### Files Changed

**FILE: setup-interactive-auth.ps1**

BEFORE (Stream 3 permissions):
```powershell
$stream3Permissions = @(
    @{ Id = "4ad84827-5578-4e18-ad7a-86530b12f884"; Name = "InformationProtectionPolicy.Read" }
    @{ Id = "572fea84-0151-49b2-9301-11cb16974376"; Name = "Policy.Read.All" }
)
```

AFTER (Stream 3 permissions — added Organization.Read.All):
```powershell
$stream3Permissions = @(
    @{ Id = "4ad84827-5578-4e18-ad7a-86530b12f884"; Name = "InformationProtectionPolicy.Read" }
    @{ Id = "572fea84-0151-49b2-9301-11cb16974376"; Name = "Policy.Read.All" }
    @{ Id = "4908d5b9-3fb2-4b1e-9336-1888b7937185"; Name = "Organization.Read.All" }
)
```

Also updated Stream 3 comment from "(2 Graph delegated permissions)" to "(3 Graph delegated permissions)".

**FILE: INTERACTIVE-AUTH-GUIDELINES.md**

- Stream 3: Added `Organization.Read.All` to the Graph delegated permissions list

### Action Required
After this code change, you must either:
1. **Re-run `setup-interactive-auth.ps1`** to recreate the app registrations with the new permissions, OR
2. **Manually add `Organization.Read.All`** (delegated) to your existing Stream 3 app registration in Azure Portal → App registrations → API permissions → Add a permission → Microsoft Graph → Delegated → Organization.Read.All → Grant admin consent

### ROLLBACK (Change 16)
Remove `Organization.Read.All` line from `$stream3Permissions` in setup-interactive-auth.ps1. Revert the INTERACTIVE-AUTH-GUIDELINES.md Stream 3 permission list.

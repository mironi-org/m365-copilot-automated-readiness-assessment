from azure.identity import ClientSecretCredential, DeviceCodeCredential, InteractiveBrowserCredential
from msgraph import GraphServiceClient
import msal
import httpx
import logging
import os
import subprocess

# Suppress Azure SDK warnings
logging.getLogger('azure.identity').setLevel(logging.ERROR)

# ═══════════════════════════════════════════════════════════════════════════════
# PER-STREAM APP REGISTRATION MODEL
# Each stream has its own app with ONLY the delegated permissions it needs.
# ═══════════════════════════════════════════════════════════════════════════════

STREAM_CLIENT_ID_MAP = {
    'M365':            'CLIENT_ID_STREAM1',
    'Entra':           'CLIENT_ID_STREAM1',
    'Defender':        'CLIENT_ID_STREAM2',
    'Purview':         'CLIENT_ID_STREAM3',
    'Power Platform':  'CLIENT_ID_STREAM4',
    'Copilot Studio':  'CLIENT_ID_STREAM4',  # Same app as Power Platform
    'A365':            'CLIENT_ID_STREAM5',
}

# Secondary API scopes each service needs beyond https://graph.microsoft.com/.default.
# Pre-warming these after the initial Graph auth lets MSAL use the cached refresh token
# to silently acquire them — avoiding extra device-code prompts during asyncio.gather.
# Secondary API scopes that need pre-warming with the per-stream credential.
# Power Platform & Copilot Studio are NOT listed here because their data
# collection uses Connect-AzAccount (PowerShell) / AzureCliCredential (Python),
# not the Stream 4 app credential.
_SECONDARY_SCOPES = {
    'Defender':       ['https://api.securitycenter.microsoft.com/.default'],
}

# Load .env file into environment variables (no external dependency)
def _load_env():
    """Load .env file if it exists (in project root, not Core folder)"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip()
                    # Strip inline comments (e.g. "value  # comment")
                    if '  #' in value:
                        value = value[:value.index('  #')].strip()
                    # Only set if not already in environment (CLI args take precedence over .env)
                    os.environ.setdefault(key.strip(), value)

# Load environment variables on import
_load_env()

# Module-level cache: per client_id credential and graph client
_credentials = {}   # {client_id: credential}
_graph_clients = {} # {client_id: GraphServiceClient}

# Legacy single-credential cache (service principal mode)
_graph_client = None
_credential = None


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
        return DeviceCodeCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            prompt_callback=_device_code_prompt
        )
    return InteractiveBrowserCredential(
        tenant_id=tenant_id,
        client_id=client_id
    )


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
            else:
                _credentials[client_id] = _create_interactive_credential(tenant_id, client_id)
        
        credential = _credentials[client_id]
        
        # Do NOT call credential.get_token() explicitly here.
        # Let the Graph SDK acquire the token lazily on its first API call.
        # Calling get_token() eagerly causes a DOUBLE device-code prompt because
        # MSAL (azure-identity 1.25.x / msal 1.36.x) does not reliably serve
        # the cached token when the SDK calls get_token() internally afterward.
        # The "Authenticated" message is printed by setup_graph_and_licenses()
        # after the first successful SDK call (subscribed_skus.get()).
        
        # For interactive with per-stream apps: use .default (admin pre-granted consent)
        scopes = ['https://graph.microsoft.com/.default']
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=scopes
        )
        
        _graph_clients[client_id] = graph_client
        
        return graph_client
    else:
        # Service principal authentication (default) — single shared credential
        if _graph_client:
            return _graph_client
        
        client_id = os.getenv('CLIENT_ID')
        client_secret = os.getenv('CLIENT_SECRET')
        
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError(
                "Missing required environment variables. Ensure .env file contains:\n"
                "  TENANT_ID=<your-tenant-id>\n"
                "  CLIENT_ID=<your-app-id>\n"
                "  CLIENT_SECRET=<your-client-secret>\n"
                "Run setup-service-principal.ps1 to create these credentials."
            )
        
        if not silent:
            print(f"[{get_timestamp()}] ℹ️     Authenticating with service principal...")
            import sys
            sys.stdout.flush()
        
        if _credential is None:
            _credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
        
        scopes = ['https://graph.microsoft.com/.default']
        
        _graph_client = GraphServiceClient(
            credentials=_credential,
            scopes=scopes
        )
        
        if not silent:
            print(f"[{get_timestamp()}] ✅ Authenticated successfully")
            import sys
            sys.stdout.flush()
        
        return _graph_client


def _resolve_interactive_client_id(services=None):
    """Resolve the correct CLIENT_ID for interactive mode based on requested services.
    
    Priority:
    1. Per-stream CLIENT_ID_STREAMx from STREAM_CLIENT_ID_MAP
    2. Legacy CLIENT_ID env var
    3. Raise error — user must run setup-interactive-auth.ps1
    
    Args:
        services: List of service names, or None
        
    Returns:
        Client ID string
        
    Raises:
        ValueError: If no CLIENT_ID_STREAMx or CLIENT_ID is configured
    """
    # Try per-stream resolution
    if services:
        for service in services:
            env_var = STREAM_CLIENT_ID_MAP.get(service)
            if env_var:
                client_id = os.getenv(env_var)
                if client_id:
                    return client_id
    
    # Fallback: legacy CLIENT_ID
    legacy = os.getenv('CLIENT_ID')
    if legacy:
        return legacy
    
    # No client ID found — fail fast with actionable guidance
    if services:
        needed = set(STREAM_CLIENT_ID_MAP[s] for s in services if s in STREAM_CLIENT_ID_MAP)
        raise ValueError(
            f"No app registration found for interactive mode.\n"
            f"Missing env vars: {', '.join(sorted(needed))}\n"
            f"Run setup-interactive-auth.ps1 to create per-stream app registrations."
        )
    raise ValueError(
        "No CLIENT_ID configured for interactive mode.\n"
        "Run setup-interactive-auth.ps1 to create per-stream app registrations."
    )

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
    else:
        # Service principal — single shared credential
        if _credential is not None:
            return _credential
        
        client_id = os.getenv('CLIENT_ID')
        client_secret = os.getenv('CLIENT_SECRET')
        
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("Missing credentials in .env file. Run setup-service-principal.ps1 first.")
        
        _credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        return _credential

def get_power_platform_credential():
    """Get credential for Power Platform APIs.
    
    Returns:
        ClientSecretCredential or InteractiveBrowserCredential instance
    """
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
    """Get HTTP client with bearer token for specific API
    
    Args:
        service_name: One of 'defender', 'power_platform'
    
    Returns:
        httpx.AsyncClient with authorization header
    """
    # Map API service names to stream names for per-stream credential resolution
    _api_to_stream = {'defender': 'Defender', 'power_platform': 'Power Platform'}
    stream_name = _api_to_stream.get(service_name)
    credential = get_shared_credential(service_name=stream_name)
    
    # Define scopes and base URLs for each service
    service_config = {
        'defender': {
            'scope': 'https://api.security.microsoft.com/.default',
            'base_url': 'https://api.security.microsoft.com'
        },
        'power_platform': {
            'scope': 'https://service.powerapps.com/.default',
            'base_url': 'https://service.powerapps.com'
        }
    }
    
    if service_name not in service_config:
        raise ValueError(f"Unknown service: {service_name}. Valid: {list(service_config.keys())}")
    
    config = service_config[service_name]
    
    # Get token for the specific scope (synchronous call)
    token = credential.get_token(config['scope'])
    
    # Create HTTP client with bearer token
    return httpx.AsyncClient(
        base_url=config['base_url'],
        headers={
            "Authorization": f"Bearer {token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        timeout=30.0
    )


def ensure_a365_interactive_signin(tenant_id=None, silent=False):
    """Trigger interactive delegated sign-in for A365 users.

    This performs interactive AuthN via Connect-MgGraph (browser popup style)
    and validates AuthZ by probing the Copilot admin catalog endpoint.

    Args:
        tenant_id: Azure tenant ID (optional)
        silent: If True, suppress status output

    Returns:
        bool: True only if interactive sign-in succeeds and endpoint authorization is confirmed
    """
    from .spinner import get_timestamp

    try:
        if not silent:
            print(f"[{get_timestamp()}] ℹ️  A365 requires interactive sign-in with an AI/Copilot admin user...")

        # Always re-run interactive auth for A365 to avoid silent reuse of prior in-process status.
        os.environ["A365_INTERACTIVE_AUTH"] = "0"

        tenant = tenant_id or os.getenv('TENANT_ID')
        if not tenant:
            os.environ["A365_INTERACTIVE_AUTH"] = "0"
            if not silent:
                print(f"[{get_timestamp()}] ⚠️  TENANT_ID is required for A365 interactive sign-in")
            return False

        client_id = os.getenv('CLIENT_ID_STREAM5', '')
        if not client_id:
            os.environ["A365_INTERACTIVE_AUTH"] = "0"
            if not silent:
                print(f"[{get_timestamp()}] ⚠️  CLIENT_ID_STREAM5 is required for A365 interactive sign-in. Run setup-interactive-auth.ps1 -Streams 5")
            return False

        # Use PowerShell Graph auth — device code or interactive browser based on auth mode.
        use_device_code = os.getenv('USE_DEVICE_CODE') == '1'

        ps_command = (
            "$ErrorActionPreference='Stop';"
            "if (-not (Get-Module -ListAvailable -Name Microsoft.Graph.Authentication)) {"
            "  Write-Host 'Microsoft.Graph PowerShell module is required for A365 interactive sign-in.' -ForegroundColor Yellow;"
            "  Write-Host 'Install with: Install-Module Microsoft.Graph -Scope CurrentUser -Force -AllowClobber' -ForegroundColor Cyan;"
            "  exit 61"
            "};"
            "Disconnect-MgGraph -ErrorAction SilentlyContinue | Out-Null;"
        )

        if use_device_code:
            ps_command += (
                "Write-Host 'A365 sign-in required now. Complete device authentication in the browser within 120 seconds.' -ForegroundColor Yellow;"
                "Write-Host 'Use https://microsoft.com/devicelogin if login.microsoft.com/device has browser issues.' -ForegroundColor Yellow;"
                f"Connect-MgGraph -TenantId '{tenant}' -ClientId '{client_id}' -NoWelcome -ContextScope Process -UseDeviceAuthentication -Scopes 'User.Read','CopilotPackages.Read.All' -ErrorAction Stop;"
            )
        else:
            ps_command += (
                "Write-Host 'A365 sign-in required now. An account picker/browser prompt should open.' -ForegroundColor Yellow;"
                "Write-Host 'If the browser prompt is hidden, bring it to front and finish sign-in.' -ForegroundColor Yellow;"
                f"Connect-MgGraph -TenantId '{tenant}' -ClientId '{client_id}' -NoWelcome -ContextScope Process -Scopes 'User.Read','CopilotPackages.Read.All' -ErrorAction Stop;"
            )

        ps_command += (
            "$ctx = Get-MgContext;"
            "if ($ctx) {"
            "  Write-Host \"[A365-DIAG] Account: $($ctx.Account)\" -ForegroundColor Cyan;"
            "  Write-Host \"[A365-DIAG] Scopes in token: $($ctx.Scopes -join ', ')\" -ForegroundColor Cyan;"
            "}"
            "try {"
            "  Invoke-MgGraphRequest -Method GET -Uri 'https://graph.microsoft.com/beta/copilot/admin/catalog/packages?$top=1' -ErrorAction Stop | Out-Null;"
            "  exit 0"
            "}"
            "catch {"
            "  Write-Host \"[A365-DIAG] API ERROR: $($_.Exception.Message)\" -ForegroundColor Red;"
            "  if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {"
            "    $code=[int]$_.Exception.Response.StatusCode;"
            "    Write-Host \"[A365-DIAG] HTTP $code\" -ForegroundColor Red;"
            "    $errBody='';"
            "    try {"
            "      $errBody = $_.Exception.Response.Content.ReadAsStringAsync().Result;"
            "      if ($errBody) { Write-Host \"[A365-DIAG] Body: $errBody\" -ForegroundColor Red }"
            "    } catch {}"
            "    if ($code -eq 403 -and $errBody -match 'licensed') { exit 44 }"
            "    if ($code -eq 401) { exit 41 }"
            "    elseif ($code -eq 403) { exit 43 }"
            "    else { exit 50 }"
            "  }"
            "  else {"
            "    Write-Host \"[A365-DIAG] Non-HTTP error: $($_.Exception.GetType().FullName)\" -ForegroundColor Red;"
            "    exit 51"
            "  }"
            "}"
        )

        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", ps_command],
            text=True
        )

        if result.returncode == 0:
            os.environ["A365_INTERACTIVE_AUTH"] = "1"
            if not silent:
                print(f"[{get_timestamp()}] ✅ A365 interactive sign-in and authorization successful")
            return True

        os.environ["A365_INTERACTIVE_AUTH"] = "0"
        if not silent:
            if result.returncode == 44:
                print(f"[{get_timestamp()}] ⚠️  Tenant is not licensed for Microsoft 365 Copilot / Agent 365.")
                print(f"[{get_timestamp()}] ℹ️  The Copilot admin catalog API requires an active Copilot license on the tenant.")
            elif result.returncode == 43:
                print(f"[{get_timestamp()}] ⚠️  Signed-in user is not authorized for Copilot admin catalog endpoint (requires AI Admin/Copilot Admin or Global Admin).")
            elif result.returncode == 41:
                print(f"[{get_timestamp()}] ⚠️  Interactive sign-in succeeded, but token is unauthorized for Copilot admin endpoint.")
            elif result.returncode == 61:
                print(f"[{get_timestamp()}] ⚠️  Microsoft.Graph PowerShell module not found. Install it and retry.")
            else:
                print(f"[{get_timestamp()}] ⚠️  A365 interactive sign-in/auth probe failed via Graph PowerShell.")
        return False
    except Exception as e:
        os.environ["A365_INTERACTIVE_AUTH"] = "0"
        if not silent:
            print(f"[{get_timestamp()}] ⚠️  A365 interactive sign-in failed: {e}")
        return False

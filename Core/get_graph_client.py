from azure.identity import ClientSecretCredential, InteractiveBrowserCredential
from msgraph import GraphServiceClient
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
                    os.environ[key.strip()] = value

# Load environment variables on import
_load_env()

# Module-level cache: per client_id credential and graph client
_credentials = {}   # {client_id: InteractiveBrowserCredential}
_graph_clients = {} # {client_id: GraphServiceClient}

# Legacy single-credential cache (service principal mode)
_graph_client = None
_credential = None

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
        
        if not silent:
            print(f"[{get_timestamp()}] ℹ️     Authenticating with interactive browser login...")
            import sys
            sys.stdout.flush()
        
        if client_id not in _credentials:
            _credentials[client_id] = InteractiveBrowserCredential(
                tenant_id=tenant_id,
                client_id=client_id
            )
        
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
        
        cred = InteractiveBrowserCredential(
            tenant_id=tenant_id,
            client_id=client_id
        )
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

        # Use PowerShell Graph interactive auth (popup experience, similar to Purview flow).
        ps_command = (
            "$ErrorActionPreference='Stop';"
            "if (-not (Get-Module -ListAvailable -Name Microsoft.Graph.Authentication)) {"
            "  Write-Host 'Microsoft.Graph PowerShell module is required for A365 interactive sign-in.' -ForegroundColor Yellow;"
            "  Write-Host 'Install with: Install-Module Microsoft.Graph -Scope CurrentUser -Force -AllowClobber' -ForegroundColor Cyan;"
            "  exit 61"
            "};"
            "Disconnect-MgGraph -ErrorAction SilentlyContinue | Out-Null;"
            "Write-Host 'A365 sign-in required now. Complete device authentication in the browser within 120 seconds.' -ForegroundColor Yellow;"
            "Write-Host 'If the browser prompt is hidden, bring it to front and finish sign-in.' -ForegroundColor Yellow;"
            f"Connect-MgGraph -TenantId '{tenant}' -NoWelcome -ContextScope Process -UseDeviceAuthentication -Scopes 'User.Read','Directory.Read.All','CopilotPackages.Read.All' -ErrorAction Stop;"
            "try {"
            "  Invoke-MgGraphRequest -Method GET -Uri 'https://graph.microsoft.com/beta/copilot/admin/catalog/packages?$top=1' -ErrorAction Stop | Out-Null;"
            "  exit 0"
            "}"
            "catch {"
            "  if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {"
            "    $code=[int]$_.Exception.Response.StatusCode;"
            "    if ($code -eq 401) { exit 41 }"
            "    elseif ($code -eq 403) { exit 43 }"
            "    else { exit 50 }"
            "  }"
            "  else { exit 51 }"
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
            if result.returncode == 43:
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

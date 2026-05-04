"""A365 Graph client helpers for delegated data collection."""

import asyncio
import json
import os
import subprocess
import tempfile

from Core.spinner import get_timestamp


async def _run_powershell_command(command):
    """Run a PowerShell command in a worker thread to avoid blocking the event loop."""
    return await asyncio.to_thread(
        subprocess.run,
        ["pwsh", "-NoProfile", "-Command", command],
        text=True,
        capture_output=False,
    )


async def get_a365_client(tenant_id=None, silent=False):
    """Authenticate interactively and fetch A365 package catalog from Graph beta.

    Args:
        tenant_id: Azure tenant ID (optional)
        silent: If True, suppress status output

    Returns:
        dict | None: Parsed Graph response for /beta/copilot/admin/catalog/packages, or None on failure
    """
    tenant = tenant_id or os.getenv("TENANT_ID")
    if not tenant:
        os.environ["A365_INTERACTIVE_AUTH"] = "0"
        if not silent:
            print(f"[{get_timestamp()}] ⚠️  TENANT_ID is required for A365 data gathering")
        return None

    temp_json = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    temp_json.close()
    token_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".token.txt")
    token_temp.close()

    temp_path = temp_json.name.replace("'", "''")
    token_path = token_temp.name.replace("'", "''")

    ps_command = (
        "$ErrorActionPreference='Stop';"
        "if (-not (Get-Module -ListAvailable -Name Microsoft.Graph.Authentication)) {"
        "  Write-Host 'Microsoft.Graph PowerShell module is required for A365 data gathering.' -ForegroundColor Yellow;"
        "  Write-Host 'Install with: Install-Module Microsoft.Graph -Scope CurrentUser -Force -AllowClobber' -ForegroundColor Cyan;"
        "  exit 61"
        "};"
        "Disconnect-MgGraph -ErrorAction SilentlyContinue | Out-Null;"
        "$scopes=@('User.Read','Directory.Read.All','CopilotPackages.Read.All');"
        "Write-Host 'A365 sign-in required now. An account picker/browser prompt should open.' -ForegroundColor Yellow;"
        "Write-Host 'Select the admin account to use for this run.' -ForegroundColor Yellow;"
        "try {"
        f"  Connect-MgGraph -TenantId '{tenant}' -NoWelcome -ContextScope Process -Scopes $scopes -ErrorAction Stop;"
        "}"
        "catch {"
        "  Write-Host 'Interactive picker failed or was blocked. Falling back to device code...' -ForegroundColor Yellow;"
        "  Write-Host 'Use https://microsoft.com/devicelogin if login.microsoft.com/device has browser issues.' -ForegroundColor Yellow;"
        f"  Connect-MgGraph -TenantId '{tenant}' -NoWelcome -ContextScope Process -UseDeviceAuthentication -Scopes $scopes -ErrorAction Stop;"
        "}"
        "try {"
        "  $response = Invoke-MgGraphRequest -Method GET -Uri 'https://graph.microsoft.com/beta/copilot/admin/catalog/packages' -ErrorAction Stop;"
        f"  $response | ConvertTo-Json -Depth 30 | Set-Content -Path '{temp_path}' -Encoding UTF8;"
        "  $_tok = $null;"
        "  try { $_tok = (Get-MgContext).AccessToken; } catch {}"
        "  if (-not $_tok) {"
        "    try {"
        "      $_r2 = Invoke-MgGraphRequest -Method GET -Uri 'https://graph.microsoft.com/v1.0/me' -OutputType HttpResponseMessage -ErrorAction Stop;"
        "      $_tok = $_r2.RequestMessage.Headers.Authorization.Parameter;"
        "    } catch {}"
        "  }"
        f"  if ($_tok) {{ $_tok | Set-Content -Path '{token_path}' -NoNewline -Encoding UTF8; }}"
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

    try:
        result = await _run_powershell_command(ps_command)

        if result.returncode != 0:
            os.environ["A365_INTERACTIVE_AUTH"] = "0"
            if not silent:
                if result.returncode == 43:
                    print(f"[{get_timestamp()}] ⚠️  Signed-in user is not authorized for Copilot admin catalog endpoint.")
                elif result.returncode == 41:
                    print(f"[{get_timestamp()}] ⚠️  Token is unauthorized for Copilot admin catalog endpoint.")
                elif result.returncode == 61:
                    print(f"[{get_timestamp()}] ⚠️  Microsoft.Graph PowerShell module not found. Install it and retry.")
                else:
                    print(f"[{get_timestamp()}] ⚠️  A365 data gathering failed via Graph PowerShell.")
            return None

        if not os.path.exists(temp_json.name):
            os.environ["A365_INTERACTIVE_AUTH"] = "0"
            if not silent:
                print(f"[{get_timestamp()}] ⚠️  A365 data gathering did not return a payload.")
            return None

        with open(temp_json.name, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if os.path.exists(token_temp.name):
            with open(token_temp.name, "r", encoding="utf-8") as f:
                access_token = f.read().strip()
            if access_token:
                payload["_access_token"] = access_token

        os.environ["A365_INTERACTIVE_AUTH"] = "1"
        return payload
    except Exception as e:
        os.environ["A365_INTERACTIVE_AUTH"] = "0"
        if not silent:
            print(f"[{get_timestamp()}] ⚠️  A365 data gathering failed: {e}")
        return None
    finally:
        try:
            if os.path.exists(temp_json.name):
                os.remove(temp_json.name)
        except OSError:
            pass
        try:
            if os.path.exists(token_temp.name):
                os.remove(token_temp.name)
        except OSError:
            pass

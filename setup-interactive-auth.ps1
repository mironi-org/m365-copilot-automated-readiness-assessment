<#
.SYNOPSIS
    STEP 2: Create Per-Stream App Registrations (Admin — One-Time)
    Creates per-stream Azure AD App Registrations for Interactive Browser Authentication.

.DESCRIPTION
    Part of the Interactive Auth setup workflow (see interactive-auth-guidelines.md):
      STEP 1: Prerequisites (modules, roles)
      STEP 2: Create Per-Stream App Registrations (Admin — One-Time)  ← THIS SCRIPT
      STEP 3: Configure .env
      STEP 4: Run the tool

    Creates ONE app registration PER STREAM with isolated delegated permissions.
    Each app gets ONLY the permissions its stream needs — enforcing least-privilege
    at the token level.

    Apps created:
    - Stream 1: "Readiness - M365 & Entra"     (22 Graph delegated permissions)
    - Stream 2: "Readiness - Defender"          (7 Graph + 1 Defender API + 2 O365 Mgmt)
    - Stream 3: "Readiness - Purview"           (2 Graph delegated permissions)
    - Stream 4: "Readiness - Power Platform"    (1 Power Platform API permission)

    Stream 5 (A365/Copilot) uses Connect-MgGraph directly — no app registration needed.

    After creation, admin consent is granted for each app and CLIENT_ID_STREAMx
    values are written to .env.

.PARAMETER Streams
    Which streams to create app registrations for.
    Accepts: All, 1, 2, 3, 4, or comma-separated (e.g. "1,2")
    Default: All

.PARAMETER Force
    Delete and recreate existing app registrations without prompting.

.EXAMPLE
    .\setup-interactive-auth.ps1
    # Creates all 4 per-stream app registrations

.EXAMPLE
    .\setup-interactive-auth.ps1 -Streams "1,2"
    # Creates only Stream 1 and Stream 2 apps

.EXAMPLE
    .\setup-interactive-auth.ps1 -Force
    # Recreates all apps (deletes existing if found)

.NOTES
    Requirements:
    - Global Administrator or Application Administrator role
    - Microsoft.Graph PowerShell module (auto-installed if missing)
    - Run: Connect-MgGraph will open browser for admin login
#>

#Requires -Version 5.1

param(
    [string]$Streams = "All",
    [switch]$Force
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

$streamConfig = @{
    1 = @{
        Name = "Readiness - M365 & Entra"
        EnvVar = "CLIENT_ID_STREAM1"
        Role = "Global Reader"
    }
    2 = @{
        Name = "Readiness - Defender"
        EnvVar = "CLIENT_ID_STREAM2"
        Role = "Security Reader"
    }
    3 = @{
        Name = "Readiness - Purview"
        EnvVar = "CLIENT_ID_STREAM3"
        Role = "Compliance Reader"
    }
    4 = @{
        Name = "Readiness - Power Platform"
        EnvVar = "CLIENT_ID_STREAM4"
        Role = "Power Platform Administrator"
    }
}

# Microsoft Graph API Resource ID
$graphResourceId = "00000003-0000-0000-c000-000000000000"
# Defender for Endpoint API
$defenderResourceId = "fc780465-2017-40d4-a0c5-307022471b92"
# Office 365 Management API
$office365MgmtResourceId = "c5393580-f805-4401-95e8-94b7a6ef2fc2"
# Power Platform API (BAP)
$powerPlatformResourceId = "00000007-0000-0000-c000-000000000000"

# ═══════════════════════════════════════════════════════════════════════════════
# STREAM 1 PERMISSIONS: Microsoft Graph — M365 + Entra
# ═══════════════════════════════════════════════════════════════════════════════

$stream1Permissions = @(
    @{ Id = "4908d5b9-3fb2-4b1e-9336-1888b7937185"; Name = "Organization.Read.All" }
    @{ Id = "06da0dbc-49e2-44d2-8312-53f166ab848a"; Name = "Directory.Read.All" }
    @{ Id = "a154be20-db9c-4678-8ab7-66f6cc099a59"; Name = "User.Read.All" }
    @{ Id = "5f8c59db-677d-491f-a6b8-5f174b11ec1d"; Name = "Group.Read.All" }
    @{ Id = "c79f8feb-a9db-4090-85f9-90d820caa0eb"; Name = "Application.Read.All" }
    @{ Id = "ebfcd32b-babb-40f4-a14b-42706e83bd28"; Name = "AccessReview.Read.All" }
    @{ Id = "572fea84-0151-49b2-9301-11cb16974376"; Name = "Policy.Read.All" }
    @{ Id = "741c54c3-0c1e-44a1-818b-3f97ab4e8c83"; Name = "RoleManagement.Read.Directory" }
    @{ Id = "aec28ec7-4d02-4e8c-b864-50163aea77eb"; Name = "UserAuthenticationMethod.Read.All" }
    @{ Id = "02e97553-ed7b-43d0-ab3c-f8bace0d040c"; Name = "Reports.Read.All" }
    @{ Id = "e4c9e354-4dc5-45b8-9e7c-e1393b0b1a20"; Name = "AuditLog.Read.All" }
    @{ Id = "205e70e5-aba6-4c52-a976-6d2d46c48043"; Name = "Sites.Read.All" }
    @{ Id = "df85f4d6-205c-4ac5-a5ea-6bf408dba283"; Name = "Files.Read.All" }
    @{ Id = "a38267a5-26b6-4d76-9493-935b7599116b"; Name = "ExternalConnection.Read.All" }
    @{ Id = "9d8982ae-4365-4f57-95e9-d6032a4c0b87"; Name = "Channel.ReadBasic.All" }
    @{ Id = "9be106e1-f4e3-4df5-bdff-e4bc531cbe43"; Name = "OnlineMeetings.Read" }
    @{ Id = "33b1df99-4b29-4548-9339-7a7b83eaeebc"; Name = "Bookings.Read.All" }
    @{ Id = "b89f9189-71a5-4e70-b041-9887f0bc7e4a"; Name = "People.Read.All" }
    @{ Id = "3a736c8a-018e-460a-b60c-863b2683e8bf"; Name = "Printer.Read.All" }
    @{ Id = "314874da-47d6-4978-88dc-cf0d37f0bb82"; Name = "DeviceManagementManagedDevices.Read.All" }
    @{ Id = "f1493658-876a-4c87-8fa7-edb559b3476a"; Name = "DeviceManagementConfiguration.Read.All" }
    @{ Id = "ba22922b-752c-446f-89d7-a2d92398fceb"; Name = "NetworkAccessPolicy.Read.All" }
)

# ═══════════════════════════════════════════════════════════════════════════════
# STREAM 2 PERMISSIONS: Defender (Graph + Defender API + O365 Mgmt)
# ═══════════════════════════════════════════════════════════════════════════════

$stream2GraphPermissions = @(
    @{ Id = "64733abd-851e-478a-bffb-e47a14b18235"; Name = "SecurityEvents.Read.All" }
    @{ Id = "b9abcc4f-94fc-4457-9141-d20ce80ec952"; Name = "SecurityIncident.Read.All" }
    @{ Id = "9cc427b4-2004-41c5-aa22-757b755e9796"; Name = "ThreatIndicators.Read.All" }
    @{ Id = "b152eca8-ea73-4a48-8c98-1a6742673d99"; Name = "ThreatHunting.Read.All" }
    @{ Id = "cac97e40-6730-457d-ad8d-4852fddab7ad"; Name = "ThreatAssessment.ReadWrite.All" }
    @{ Id = "d04bb851-cb7c-4146-97c7-ca3e71baf56c"; Name = "IdentityRiskyUser.Read.All" }
    @{ Id = "8f6a01e7-0391-4ee5-aa22-a3af122cef27"; Name = "IdentityRiskEvent.Read.All" }
)

$stream2DefenderPermissions = @(
    @{ Id = "fbd3d33a-b1f5-4573-906c-51b39682fbcf"; Name = "Machine.Read" }
)

$stream2Office365Permissions = @(
    @{ Id = "594c1fb6-4f81-4475-ae41-0c394909246c"; Name = "ActivityFeed.Read" }
    @{ Id = "e2cea78f-e743-4d8f-a16a-75b629a038ae"; Name = "ServiceHealth.Read" }
)

# ═══════════════════════════════════════════════════════════════════════════════
# STREAM 3 PERMISSIONS: Purview (minimal Graph)
# ═══════════════════════════════════════════════════════════════════════════════

$stream3Permissions = @(
    @{ Id = "4ad84827-5578-4e18-ad7a-86530b12f884"; Name = "InformationProtectionPolicy.Read" }
    @{ Id = "572fea84-0151-49b2-9301-11cb16974376"; Name = "Policy.Read.All" }
)

# ═══════════════════════════════════════════════════════════════════════════════
# STREAM 4 PERMISSIONS: Power Platform API + minimal Graph
# ═══════════════════════════════════════════════════════════════════════════════

$stream4GraphPermissions = @(
    @{ Id = "4908d5b9-3fb2-4b1e-9336-1888b7937185"; Name = "Organization.Read.All" }
)

$stream4PowerPlatformPermissions = @(
    @{ Id = "8578e004-a5c6-46e7-913e-12f58912df43"; Name = "user_impersonation" }
)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

function Write-Success { param($Message) Write-Host "  ✓ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "  ℹ $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "  ⚠ $Message" -ForegroundColor Yellow }
function Write-Fail { param($Message) Write-Host "  ✗ $Message" -ForegroundColor Red }

function New-StreamAppRegistration {
    param(
        [int]$StreamNumber,
        [string]$AppName,
        [array]$RequiredResourceAccess
    )

    Write-Host ""
    Write-Host "  ─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  Stream $StreamNumber`: $AppName" -ForegroundColor White
    Write-Host "  ─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

    # Check for existing
    $existingApp = Get-MgApplication -Filter "displayName eq '$AppName'" -ErrorAction SilentlyContinue | Select-Object -First 1

    if ($existingApp) {
        if ($Force) {
            Write-Warn "Deleting existing app: $AppName (AppId: $($existingApp.AppId))"
            Remove-MgApplication -ApplicationId $existingApp.Id
            Start-Sleep -Seconds 2
        } else {
            Write-Warn "App '$AppName' already exists (AppId: $($existingApp.AppId))"
            $response = Read-Host "    Delete and recreate? (y/N)"
            if ($response -eq 'y' -or $response -eq 'Y') {
                Remove-MgApplication -ApplicationId $existingApp.Id
                Start-Sleep -Seconds 2
            } else {
                Write-Info "Keeping existing app"
                return $existingApp.AppId
            }
        }
    }

    # Create public client app
    $publicClient = @{
        RedirectUris = @("http://localhost")
    }

    try {
        $app = New-MgApplication `
            -DisplayName $AppName `
            -SignInAudience "AzureADMyOrg" `
            -PublicClient $publicClient `
            -IsFallbackPublicClient `
            -RequiredResourceAccess $RequiredResourceAccess `
            -ErrorAction Stop

        if (-not $app -or -not $app.AppId) {
            throw "App creation returned empty result"
        }

        Write-Success "Created: $AppName"
        Write-Success "Client ID: $($app.AppId)"
        return $app.AppId
    } catch {
        Write-Fail "Failed to create '$AppName': $_"
        return $null
    }
}

function Grant-AdminConsent {
    param(
        [string]$AppId,
        [string]$TenantId,
        [string]$AppName
    )

    Write-Info "Granting admin consent for: $AppName"

    # Ensure service principal exists (required for consent to work)
    $sp = Get-MgServicePrincipal -Filter "appId eq '$AppId'" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $sp) {
        Write-Info "Creating service principal for $AppName..."
        $sp = New-MgServicePrincipal -AppId $AppId -ErrorAction Stop
        Write-Success "Service principal created: $($sp.Id)"
    }

    $adminConsentUrl = "https://login.microsoftonline.com/$TenantId/adminconsent?client_id=$AppId"
    Start-Process $adminConsentUrl

    Write-Host "    → Browser opened. Click 'Accept' then return here." -ForegroundColor Gray
    Write-Host "    → 'Can't reach this page' after Accept is NORMAL." -ForegroundColor Gray
    $null = Read-Host "    Press ENTER after accepting consent"
    Write-Success "Admin consent granted for $AppName"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   M365 Copilot Readiness — Per-Stream App Registration Setup" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Security model: ONE app per stream = isolated permissions per token" -ForegroundColor White
Write-Host "  Each app gets ONLY the delegated permissions its stream needs." -ForegroundColor White
Write-Host ""

# Parse streams
$selectedStreams = @()
if ($Streams -eq "All") {
    $selectedStreams = @(1, 2, 3, 4)
} else {
    $selectedStreams = $Streams -split "," | ForEach-Object { [int]$_.Trim() } | Where-Object { $_ -ge 1 -and $_ -le 4 }
}

Write-Info "Streams to configure: $($selectedStreams -join ', ')"
foreach ($s in $selectedStreams) {
    $cfg = $streamConfig[$s]
    Write-Host "    Stream $s`: $($cfg.Name) → $($cfg.EnvVar) (Role: $($cfg.Role))" -ForegroundColor Gray
}

# ─── Check/Install Microsoft.Graph ───
Write-Host ""
Write-Info "Checking Microsoft.Graph PowerShell module..."

if (-not (Get-Module -ListAvailable -Name Microsoft.Graph.Applications)) {
    Write-Warn "Microsoft.Graph not found. Installing..."
    try {
        Install-Module Microsoft.Graph -Scope CurrentUser -Force -AllowClobber
        Write-Success "Microsoft.Graph installed"
    } catch {
        Write-Fail "Failed to install Microsoft.Graph: $_"
        exit 1
    }
} else {
    Write-Success "Microsoft.Graph module available"
}

Import-Module Microsoft.Graph.Authentication -Force
Import-Module Microsoft.Graph.Applications -Force

# ─── Connect to Microsoft Graph ───
Write-Host ""
Write-Info "Connecting to Microsoft Graph (browser will open for admin login)..."

try {
    Connect-MgGraph -Scopes "Application.ReadWrite.All", "Directory.Read.All" -ContextScope Process -NoWelcome -ErrorAction Stop
    $context = Get-MgContext

    if (-not $context -or -not $context.TenantId) {
        throw "Authentication failed or was cancelled"
    }

    Write-Success "Connected to tenant: $($context.TenantId)"
} catch {
    Write-Fail "Failed to connect: $_"
    exit 1
}

# ─── Check for Defender / O365 Mgmt service principals (needed for Stream 2) ───
$defenderSPExists = $false
$office365SPExists = $false

if ($selectedStreams -contains 2) {
    $defenderSP = Get-MgServicePrincipal -Filter "appId eq '$defenderResourceId'" -ErrorAction SilentlyContinue
    $defenderSPExists = $null -ne $defenderSP
    if (-not $defenderSPExists) {
        Write-Warn "Defender for Endpoint API not found in tenant (activate Defender XDR first)"
    }

    $office365SP = Get-MgServicePrincipal -Filter "appId eq '$office365MgmtResourceId'" -ErrorAction SilentlyContinue
    $office365SPExists = $null -ne $office365SP
    if (-not $office365SPExists) {
        Write-Warn "Office 365 Management API not found in tenant"
    }
}

if ($selectedStreams -contains 2 -and -not $defenderSPExists) {
    Write-Host "" -ForegroundColor Red
    Write-Host "❌ Defender for Endpoint was NOT found in your tenant." -ForegroundColor Red
    Write-Host "   Cannot grant Defender permissions to the Stream 2 app." -ForegroundColor Red
    Write-Host "   To enable Stream 2 (Defender), activate Defender for Endpoint (XDR) in your tenant before running this script." -ForegroundColor Red
    Write-Host "   Enabling Defender will create the required API and allow permission assignment." -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "   There is no need to continue to the assessment for Stream 2 until Defender is enabled." -ForegroundColor Red
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# CREATE PER-STREAM APPS
# ═══════════════════════════════════════════════════════════════════════════════

$results = @{}

# ─── STREAM 1 ───
if ($selectedStreams -contains 1) {
    $resourceAccess = @(
        @{
            ResourceAppId = $graphResourceId
            ResourceAccess = @($stream1Permissions | ForEach-Object {
                @{ Id = $_.Id; Type = "Scope" }
            })
        }
    )

    $clientId = New-StreamAppRegistration -StreamNumber 1 -AppName $streamConfig[1].Name -RequiredResourceAccess $resourceAccess
    if ($clientId) { $results[1] = $clientId }
}

# ─── STREAM 2 ───
if ($selectedStreams -contains 2) {
    $resourceAccess = @(
        @{
            ResourceAppId = $graphResourceId
            ResourceAccess = @($stream2GraphPermissions | ForEach-Object {
                @{ Id = $_.Id; Type = "Scope" }
            })
        }
    )

    # Add Defender API if available
    if ($defenderSPExists) {
        $resourceAccess += @{
            ResourceAppId = $defenderResourceId
            ResourceAccess = @($stream2DefenderPermissions | ForEach-Object {
                @{ Id = $_.Id; Type = "Scope" }
            })
        }
    }

    # Add O365 Management API if available
    if ($office365SPExists) {
        $resourceAccess += @{
            ResourceAppId = $office365MgmtResourceId
            ResourceAccess = @($stream2Office365Permissions | ForEach-Object {
                @{ Id = $_.Id; Type = "Scope" }
            })
        }
    }

    $clientId = New-StreamAppRegistration -StreamNumber 2 -AppName $streamConfig[2].Name -RequiredResourceAccess $resourceAccess
    if ($clientId) { $results[2] = $clientId }
}

# ─── STREAM 3 ───
if ($selectedStreams -contains 3) {
    $resourceAccess = @(
        @{
            ResourceAppId = $graphResourceId
            ResourceAccess = @($stream3Permissions | ForEach-Object {
                @{ Id = $_.Id; Type = "Scope" }
            })
        }
    )

    $clientId = New-StreamAppRegistration -StreamNumber 3 -AppName $streamConfig[3].Name -RequiredResourceAccess $resourceAccess
    if ($clientId) { $results[3] = $clientId }
}

# ─── STREAM 4 ───
# Stream 4 app ONLY needs Graph (Organization.Read.All for license queries).
# Power Platform data is collected via Connect-AzAccount (Az PowerShell) in the
# PowerShell collector script — it does NOT use this app registration.
if ($selectedStreams -contains 4) {
    $resourceAccess = @(
        @{
            ResourceAppId = $graphResourceId
            ResourceAccess = @($stream4GraphPermissions | ForEach-Object {
                @{ Id = $_.Id; Type = "Scope" }
            })
        }
    )

    $clientId = New-StreamAppRegistration -StreamNumber 4 -AppName $streamConfig[4].Name -RequiredResourceAccess $resourceAccess
    if ($clientId) { $results[4] = $clientId }
}

# ═══════════════════════════════════════════════════════════════════════════════
# GRANT ADMIN CONSENT PER APP
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "   Granting Admin Consent (one browser prompt per app)" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Yellow

foreach ($streamNum in ($results.Keys | Sort-Object)) {
    $appId = $results[$streamNum]
    $appName = $streamConfig[$streamNum].Name
    Grant-AdminConsent -AppId $appId -TenantId $context.TenantId -AppName $appName
}

# ═══════════════════════════════════════════════════════════════════════════════
# WRITE .ENV FILE
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Info "Updating .env file..."

$envPath = Join-Path $PSScriptRoot ".env"

# Read existing .env values (preserve CLIENT_IDs from prior runs)
$existingVars = @{}
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match "^(CLIENT_ID_STREAM\d+|TENANT_ID|AUTH_MODE)=(.+)$") {
            $existingVars[$Matches[1]] = $Matches[2]
        }
    }
    # Backup before overwriting
    $backup = "$envPath.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $envPath $backup
    Write-Info "Backed up existing .env → $backup"
}

# Merge: new results override, existing values preserved
foreach ($streamNum in ($results.Keys)) {
    $envVar = $streamConfig[$streamNum].EnvVar
    $existingVars[$envVar] = $results[$streamNum]
}

# Use tenant from current Graph context
$existingVars["TENANT_ID"] = $context.TenantId
$existingVars["AUTH_MODE"] = "interactive"

# Build new .env content
$envLines = @(
    "# M365 Copilot Readiness — Interactive Auth (Per-Stream)"
    "# Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "# Security: Each stream has its own app with isolated permissions"
    ""
    "TENANT_ID=$($existingVars['TENANT_ID'])"
    "AUTH_MODE=interactive"
    ""
    "# Per-stream app registration Client IDs"
)

foreach ($streamNum in (1..4)) {
    $envVar = $streamConfig[$streamNum].EnvVar
    if ($existingVars.ContainsKey($envVar) -and $existingVars[$envVar]) {
        $envLines += "$envVar=$($existingVars[$envVar])"
    } else {
        $envLines += "# $envVar=  # Not configured yet"
    }
}

$envLines += ""
$envLines += "# Stream 5 (A365/Copilot) uses Connect-MgGraph directly — no CLIENT_ID needed"
$envLines += ""
$envLines += "# NO CLIENT_SECRET NEEDED — all apps are public clients (delegated auth)"

$envLines -join "`n" | Out-File -FilePath $envPath -Encoding UTF8 -Force
Write-Success ".env updated: $envPath"

# ─── Ensure .gitignore covers .env ───
$gitignorePath = Join-Path $PSScriptRoot ".gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw
    if ($gitignoreContent -notmatch "\.env") {
        Add-Content -Path $gitignorePath -Value "`n# Environment variables`n.env`n.env.*`n"
        Write-Success "Added .env to .gitignore"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "   ✓ PER-STREAM APP REGISTRATION SETUP COMPLETE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

Write-Host "  Apps Created:" -ForegroundColor White
foreach ($streamNum in ($results.Keys | Sort-Object)) {
    $cfg = $streamConfig[$streamNum]
    Write-Host "    Stream $streamNum`: $($cfg.Name)" -ForegroundColor Cyan
    Write-Host "             $($cfg.EnvVar) = $($results[$streamNum])" -ForegroundColor Gray
    Write-Host "             Required role: $($cfg.Role)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Run Examples:" -ForegroundColor Yellow
Write-Host "    python main.py --auth-mode interactive --services M365 Entra     # Stream 1" -ForegroundColor Cyan
Write-Host "    python main.py --auth-mode interactive --services Defender        # Stream 2" -ForegroundColor Cyan
Write-Host "    python main.py --auth-mode interactive --services Purview         # Stream 3" -ForegroundColor Cyan
Write-Host '    python main.py --auth-mode interactive --services "Power Platform"  # Stream 4' -ForegroundColor Cyan
Write-Host "    python main.py --auth-mode interactive                            # All" -ForegroundColor Cyan
Write-Host ""

# Disconnect
Disconnect-MgGraph -ErrorAction SilentlyContinue | Out-Null
Write-Success "Disconnected from Microsoft Graph"
Write-Host ""
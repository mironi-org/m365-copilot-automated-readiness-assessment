<#
.SYNOPSIS
    Creates Azure AD App Registration for Interactive Browser Authentication (Delegated Permissions)
    
.DESCRIPTION
    This script creates a public client app registration with delegated permissions per stream:
    - Stream 1: Microsoft Graph (M365 + Entra) - Global Reader
    - Stream 2: Defender APIs - Security Reader
    - Stream 3: Purview (minimal - PowerShell handles its own auth)
    - Stream 4: Power Platform (no Graph permissions - PowerShell handles its own auth)
    - Stream 5: A365/Copilot (no Graph permissions - PowerShell handles its own auth)
    
    You can choose which streams to configure, or configure all at once.
    
.PARAMETER Streams
    Which streams to configure. Accepts: All, 1, 2, 3, or comma-separated (e.g. "1,2")
    Default: All
    
.EXAMPLE
    .\setup-interactive-auth.ps1
    # Configures all streams

.EXAMPLE
    .\setup-interactive-auth.ps1 -Streams "1,2"
    # Configures only Stream 1 (Graph) and Stream 2 (Defender)

.EXAMPLE
    .\setup-interactive-auth.ps1 -Streams "2"
    # Configures only Stream 2 (Defender) - for Security team

.EXAMPLE
    .\setup-interactive-auth.ps1 -Streams "1" -RunAssessment
    # Creates app registration for Stream 1 AND immediately runs the assessment

.EXAMPLE
    .\setup-interactive-auth.ps1 -RunAssessment
    # Creates combined app registration AND runs all streams
    
.NOTES
    Requirements:
    - Global Administrator or Application Administrator role
    - Microsoft.Graph PowerShell module (auto-installed if missing)
#>

#Requires -Version 5.1

param(
    [string]$Streams = "All",
    [switch]$RunAssessment
)

# Configuration
$streamAppNames = @{
    1 = "M365 Copilot Readiness - Stream 1 (Graph)"
    2 = "M365 Copilot Readiness - Stream 2 (Defender)"
    3 = "M365 Copilot Readiness - Stream 3 (Purview)"
}

# Parse streams parameter early (needed for AppName logic)
$selectedStreams = @()
if ($Streams -eq "All") {
    $selectedStreams = @(1, 2, 3)
} else {
    $selectedStreams = $Streams -split "," | ForEach-Object { [int]$_.Trim() }
}

# When All streams: single combined app. When specific stream(s): dedicated app per stream
if ($Streams -eq "All") {
    $AppName = "M365 Copilot Readiness - Interactive Auth"
} elseif ($selectedStreams.Count -eq 1) {
    $AppName = $streamAppNames[$selectedStreams[0]]
} else {
    $AppName = "M365 Copilot Readiness - Interactive Auth"
}

# Color output
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Fail { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }

Write-Host "`n=============================================================================" -ForegroundColor Cyan
Write-Host "   M365 Copilot Readiness Tool - Interactive Auth Setup (Delegated)" -ForegroundColor Cyan
Write-Host "=============================================================================" -ForegroundColor Cyan
Write-Host ""

# Display selected streams
if ($Streams -eq "All") {
    Write-Info "Configuring ALL streams (1: Graph, 2: Defender, 3: Purview)"
} else {
    $streamNames = @{ 1 = "Graph (M365/Entra)"; 2 = "Defender"; 3 = "Purview" }
    $selectedNames = ($selectedStreams | ForEach-Object { $streamNames[$_] }) -join ", "
    Write-Info "Configuring streams: $selectedNames"
}

Write-Host ""
Write-Host "  Stream 1: Microsoft Graph (M365 + Entra) — requires Global Reader" -ForegroundColor White
Write-Host "  Stream 2: Defender APIs — requires Security Reader" -ForegroundColor White
Write-Host "  Stream 3: Purview (minimal Graph perms) — requires Compliance Admin" -ForegroundColor White
Write-Host "  Stream 4: Power Platform — no Graph perms needed (PowerShell auth)" -ForegroundColor Gray
Write-Host "  Stream 5: A365/Copilot — no Graph perms needed (device code auth)" -ForegroundColor Gray
Write-Host ""

# Check required PowerShell modules
if (Test-Path "$PSScriptRoot\Check-PSModules.ps1") {
    . "$PSScriptRoot\Check-PSModules.ps1"
    if (-not (Test-RequiredModules -ScriptType "Setup")) {
        exit 1
    }
}

# Step 1: Check/Install Microsoft.Graph PowerShell
Write-Info "Checking for Microsoft.Graph PowerShell module..."
if (-not (Get-Module -ListAvailable -Name Microsoft.Graph.Applications)) {
    Write-Warn "Microsoft.Graph module not found. Installing..."
    try {
        Install-Module Microsoft.Graph -Scope CurrentUser -Force -AllowClobber
        Write-Success "Microsoft.Graph module installed"
    } catch {
        Write-Fail "Failed to install Microsoft.Graph module: $_"
        exit 1
    }
} else {
    Write-Success "Microsoft.Graph module found"
}

# Force import
Write-Info "Loading Microsoft.Graph modules..."
try {
    Import-Module Microsoft.Graph.Authentication -Force
    Import-Module Microsoft.Graph.Applications -Force
    Write-Success "Modules loaded"
} catch {
    Write-Warn "Module import issue. Close PowerShell and run script in fresh session."
    exit 1
}

# Step 2: Connect to Microsoft Graph
Write-Info "Connecting to Microsoft Graph..."
Write-Info "Browser will open for authentication (requires Global Admin or Application Admin)"

try {
    Connect-MgGraph -Scopes "Application.ReadWrite.All", "Directory.Read.All" -ContextScope Process -NoWelcome -ErrorAction Stop
    $context = Get-MgContext
    
    if (-not $context -or -not $context.TenantId) {
        throw "Authentication failed or was cancelled"
    }
    
    Write-Success "Connected to tenant: $($context.TenantId)"
} catch {
    Write-Fail "Failed to connect to Microsoft Graph: $_"
    Write-Host "`nPlease complete the browser authentication to continue.`n" -ForegroundColor Yellow
    exit 1
}

# Step 3: Check for existing app registration
Write-Info "Checking for existing app registration..."
$existingApp = Get-MgApplication -Filter "displayName eq '$AppName'" -ErrorAction SilentlyContinue | Select-Object -First 1

$skipCreation = $false
if ($existingApp) {
    Write-Warn "App registration '$AppName' already exists (AppId: $($existingApp.AppId))"
    $response = Read-Host "Do you want to delete and recreate it? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Remove-MgApplication -ApplicationId $existingApp.Id
        Write-Success "Existing app deleted"
    } else {
        Write-Info "Using existing app registration"
        $app = $existingApp
        $skipCreation = $true
    }
}

# Step 4: Create Public Client App Registration
if (-not $skipCreation) {
    Write-Info "Creating public client app registration: $AppName"
    
    # Public client with localhost redirect for InteractiveBrowserCredential
    $publicClient = @{
        RedirectUris = @("http://localhost")
    }
    
    try {
        $app = New-MgApplication `
            -DisplayName $AppName `
            -SignInAudience "AzureADMyOrg" `
            -PublicClient $publicClient `
            -IsFallbackPublicClient $true -ErrorAction Stop
    } catch {
        Write-Fail "Failed to create app registration: $_"
        Write-Host "`nYou need Application Administrator or Global Administrator role." -ForegroundColor Yellow
        exit 1
    }
    
    if (-not $app -or -not $app.AppId) {
        Write-Fail "App registration creation returned empty result."
        Write-Host "Ensure you have Application Administrator or Global Administrator role." -ForegroundColor Yellow
        exit 1
    }
    
    Write-Success "App created: $($app.DisplayName)"
    Write-Success "Application (Client) ID: $($app.AppId)"
    Write-Host ""
    Write-Host "  ┌────────────────────────────────────────────────────┐" -ForegroundColor Green
    Write-Host "  │  PUBLIC CLIENT — No secret required!               │" -ForegroundColor Green
    Write-Host "  │  'Allow public client flows' = Yes (auto-set)     │" -ForegroundColor Green
    Write-Host "  │  Redirect URI: http://localhost                    │" -ForegroundColor Green
    Write-Host "  └────────────────────────────────────────────────────┘" -ForegroundColor Green
    Write-Host ""
}

# Step 5: Define Delegated Permissions per Stream
Write-Info "Configuring delegated permissions for selected streams..."

# Microsoft Graph API Resource ID
$graphResourceId = "00000003-0000-0000-c000-000000000000"

# ═══════════════════════════════════════════════════════════════════════════════
# STREAM 1: Microsoft Graph — M365 + Entra (User Role: Global Reader)
# ═══════════════════════════════════════════════════════════════════════════════
$stream1Permissions = @(
    # Core Directory & Organization
    @{ Id = "a154be20-db9c-4678-8ab7-66f6cc099a59"; Name = "User.Read.All" }
    @{ Id = "06da0dbc-49e2-44d2-8312-53f166ab848a"; Name = "Directory.Read.All" }
    @{ Id = "4b46f140-f6f5-4dba-a41a-49ec8cd0e372"; Name = "Organization.Read.All" }
    
    # Policy & Role Management
    @{ Id = "572fea84-0151-49b2-9301-11cb16974571"; Name = "Policy.Read.All" }
    @{ Id = "741c54c3-0c1e-44a1-818b-3f97ab4e8c83"; Name = "RoleManagement.Read.Directory" }
    @{ Id = "aec28ec7-4d02-4e8c-b864-50163aea77eb"; Name = "UserAuthenticationMethod.Read.All" }
    @{ Id = "ebfcd32b-babb-40f4-a14b-42706e83bd28"; Name = "AccessReview.Read.All" }
    
    # Device Management
    @{ Id = "f6a3db3e-f7e8-4ed2-a414-557c8c9830be"; Name = "DeviceManagementManagedDevices.Read.All" }
    @{ Id = "f1493658-876a-4c87-8571-7b3e2d43203c"; Name = "DeviceManagementConfiguration.Read.All" }
    
    # Network Access (Preview)
    @{ Id = "ba1ba90b-2d8f-487e-9f16-80728d85bb5c"; Name = "NetworkAccessPolicy.Read.All" }
    
    # Applications
    @{ Id = "c79f8c76-f2a0-44d0-a5e2-dbeb5be3791b"; Name = "Application.Read.All" }
    
    # Audit & Reports
    @{ Id = "e4c9e354-4dc5-45b8-9e7c-e1393b0b1a20"; Name = "AuditLog.Read.All" }
    @{ Id = "02e97553-ed7b-43d0-ab3c-f8bace0d040c"; Name = "Reports.Read.All" }
    
    # SharePoint & OneDrive
    @{ Id = "205e70e5-aba6-4c52-a36b-21726571567a"; Name = "Sites.Read.All" }
    @{ Id = "10465720-29dd-4523-a11a-6a75c743c9d9"; Name = "Files.Read.All" }
    
    # Graph Connectors
    @{ Id = "a38267a5-26b6-4d76-9c9a-4fb26f9c2689"; Name = "ExternalConnection.Read.All" }
    
    # Teams
    @{ Id = "9d8982ae-4365-4f57-95e9-d6032a4c0b87"; Name = "Channel.ReadBasic.All" }
    @{ Id = "a65f2972-a4f8-4f5e-afd7-69ccb046d5dc"; Name = "OnlineMeetings.Read" }
    
    # Bookings & People
    @{ Id = "33b1df99-4b29-4548-9339-7a7b83eaeebc"; Name = "Bookings.Read.All" }
    @{ Id = "ba47897c-39ec-4d83-8086-ee8256fa737d"; Name = "People.Read.All" }
    
    # Specialized
    @{ Id = "90c0fe26-aa48-4005-95f1-1a7b26d44b32"; Name = "Printer.Read.All" }
    @{ Id = "45124f67-6f5a-4aa6-ac16-50b9a0d03be8"; Name = "InformationProtectionPolicy.Read" }
)

# ═══════════════════════════════════════════════════════════════════════════════
# STREAM 2: Defender (User Role: Security Reader)
# ═══════════════════════════════════════════════════════════════════════════════
$stream2GraphPermissions = @(
    # Security & Threat Intelligence
    @{ Id = "64733abd-851e-478a-bffb-e47a14b18235"; Name = "SecurityEvents.Read.All" }
    @{ Id = "53e6783e-b127-4a35-ab3a-6a52d80a9077"; Name = "SecurityIncident.Read.All" }
    @{ Id = "9cc427b4-2004-41c5-aa22-757b755e9796"; Name = "ThreatIndicators.Read.All" }
    @{ Id = "b152eca8-ea73-4a48-8c98-1a6742673d99"; Name = "ThreatHunting.Read.All" }
    @{ Id = "cac97e40-6730-457d-ad8d-4852fddab7ad"; Name = "ThreatAssessment.Read.All" }
    
    # Identity Protection
    @{ Id = "d04bb851-cb7c-4146-97c7-ca3e71baf56c"; Name = "IdentityRiskyUser.Read.All" }
    @{ Id = "8f6a01e7-0391-4ee5-aa22-a3af122cef27"; Name = "IdentityRiskEvent.Read.All" }
)

# Defender for Endpoint API — Delegated
$defenderResourceId = "fc780465-2017-40d4-a0c5-307022471b92"
$stream2DefenderPermissions = @(
    @{ Id = "ea8291d3-4b9a-44b5-bc3a-6cea3026dc79"; Name = "Machine.Read.All" }
)

# Office 365 Management API — Delegated
$office365MgmtResourceId = "c5393580-f805-4401-95e8-94b7a6ef2fc2"
$stream2Office365Permissions = @(
    @{ Id = "594c1fb6-4f81-4475-ae41-0c394909246c"; Name = "ActivityFeed.Read" }
    @{ Id = "e2cea78f-e743-4d8f-a16a-75b629a038ae"; Name = "ServiceHealth.Read" }
)

# ═══════════════════════════════════════════════════════════════════════════════
# STREAM 3: Purview (User Role: Compliance Reader / Compliance Admin)
# ═══════════════════════════════════════════════════════════════════════════════
$stream3Permissions = @(
    @{ Id = "45124f67-6f5a-4aa6-ac16-50b9a0d03be8"; Name = "InformationProtectionPolicy.Read" }
)

# ═══════════════════════════════════════════════════════════════════════════════
# Build permissions based on selected streams
# ═══════════════════════════════════════════════════════════════════════════════

$allGraphDelegated = @()
$includeDefender = $false
$includeOffice365 = $false

if ($selectedStreams -contains 1) {
    $allGraphDelegated += $stream1Permissions
    Write-Info "  → Stream 1: Adding $($stream1Permissions.Count) Graph delegated permissions (M365 + Entra)"
}

if ($selectedStreams -contains 2) {
    $allGraphDelegated += $stream2GraphPermissions
    $includeDefender = $true
    $includeOffice365 = $true
    Write-Info "  → Stream 2: Adding $($stream2GraphPermissions.Count) Graph security permissions + Defender API + O365 Management API"
}

if ($selectedStreams -contains 3) {
    # Only add if not already present from Stream 1
    $existingIds = $allGraphDelegated | ForEach-Object { $_.Id }
    foreach ($perm in $stream3Permissions) {
        if ($perm.Id -notin $existingIds) {
            $allGraphDelegated += $perm
        }
    }
    Write-Info "  → Stream 3: Adding Purview Graph permission (InformationProtectionPolicy.Read)"
}

# Remove duplicates (by Id)
$uniqueGraph = @{}
foreach ($perm in $allGraphDelegated) {
    if (-not $uniqueGraph.ContainsKey($perm.Id)) {
        $uniqueGraph[$perm.Id] = $perm
    }
}
$allGraphDelegated = $uniqueGraph.Values | Sort-Object Name

Write-Host ""
Write-Info "Total unique Graph delegated permissions: $($allGraphDelegated.Count)"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: Build RequiredResourceAccess and update app
# ═══════════════════════════════════════════════════════════════════════════════

$requiredResourceAccess = @()

# Microsoft Graph — Delegated (Scope type)
$graphResourceAccess = @{
    ResourceAppId = $graphResourceId
    ResourceAccess = @($allGraphDelegated | ForEach-Object {
        @{
            Id = $_.Id
            Type = "Scope"  # Delegated permission
        }
    })
}
$requiredResourceAccess += $graphResourceAccess

# Defender for Endpoint API — Delegated
if ($includeDefender) {
    # Check if Defender service principal exists in tenant
    $defenderSP = Get-MgServicePrincipal -Filter "appId eq '$defenderResourceId'" -ErrorAction SilentlyContinue
    
    if ($defenderSP) {
        $defenderResourceAccess = @{
            ResourceAppId = $defenderResourceId
            ResourceAccess = @($stream2DefenderPermissions | ForEach-Object {
                @{
                    Id = $_.Id
                    Type = "Scope"  # Delegated permission
                }
            })
        }
        $requiredResourceAccess += $defenderResourceAccess
        Write-Success "Defender for Endpoint API found in tenant"
    } else {
        Write-Warn "Defender for Endpoint API not found in tenant"
        Write-Warn "  → Defender XDR must be activated first (see prereq.md)"
        Write-Warn "  → Skipping Defender API permissions (Graph security permissions still added)"
    }
}

# Office 365 Management API — Delegated
if ($includeOffice365) {
    $office365SP = Get-MgServicePrincipal -Filter "appId eq '$office365MgmtResourceId'" -ErrorAction SilentlyContinue
    
    if ($office365SP) {
        $office365ResourceAccess = @{
            ResourceAppId = $office365MgmtResourceId
            ResourceAccess = @($stream2Office365Permissions | ForEach-Object {
                @{
                    Id = $_.Id
                    Type = "Scope"  # Delegated permission
                }
            })
        }
        $requiredResourceAccess += $office365ResourceAccess
        Write-Success "Office 365 Management API found in tenant"
    } else {
        Write-Warn "Office 365 Management API not found in tenant — skipping"
    }
}

# Update the app with permissions
Update-MgApplication -ApplicationId $app.Id -RequiredResourceAccess $requiredResourceAccess
Write-Success "Delegated permissions configured on app registration"

# Display configured permissions
Write-Host "`nConfigured Delegated Permissions:" -ForegroundColor Yellow

if ($selectedStreams -contains 1) {
    Write-Host "  Stream 1 — Microsoft Graph (M365 + Entra):" -ForegroundColor White
    foreach ($perm in ($stream1Permissions | Sort-Object Name)) {
        Write-Host "    - $($perm.Name)" -ForegroundColor Gray
    }
}

if ($selectedStreams -contains 2) {
    Write-Host "  Stream 2 — Microsoft Graph (Security):" -ForegroundColor White
    foreach ($perm in ($stream2GraphPermissions | Sort-Object Name)) {
        Write-Host "    - $($perm.Name)" -ForegroundColor Gray
    }
    if ($defenderSP) {
        Write-Host "  Stream 2 — Defender for Endpoint API:" -ForegroundColor White
        foreach ($perm in $stream2DefenderPermissions) {
            Write-Host "    - $($perm.Name)" -ForegroundColor Gray
        }
    }
    if ($office365SP) {
        Write-Host "  Stream 2 — Office 365 Management API:" -ForegroundColor White
        foreach ($perm in $stream2Office365Permissions) {
            Write-Host "    - $($perm.Name)" -ForegroundColor Gray
        }
    }
}

if ($selectedStreams -contains 3) {
    Write-Host "  Stream 3 — Purview:" -ForegroundColor White
    foreach ($perm in $stream3Permissions) {
        Write-Host "    - $($perm.Name)" -ForegroundColor Gray
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 7: Grant Admin Consent
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Info "Opening browser to grant admin consent for delegated permissions..."
Write-Host "`n  This will grant consent for all configured delegated permissions" -ForegroundColor Yellow
Write-Host "  You'll see a consent screen — click 'Accept' to continue`n" -ForegroundColor Yellow

# Build admin consent URL
$adminConsentUrl = "https://login.microsoftonline.com/$($context.TenantId)/adminconsent?client_id=$($app.AppId)"

# Open browser for admin consent
Start-Process $adminConsentUrl

Write-Host "Waiting for admin consent..." -ForegroundColor Cyan
Write-Host "  • Browser opened with consent page" -ForegroundColor Gray
Write-Host "  • Click 'Accept' in the browser" -ForegroundColor Gray
Write-Host "  • You'll be redirected to localhost (that's EXPECTED)" -ForegroundColor Gray
Write-Host "  • Browser will show 'Can't reach this page' — that's NORMAL" -ForegroundColor Gray
Write-Host "  • Close the browser tab and return here" -ForegroundColor Gray
Write-Host "`nPress ENTER after you've clicked Accept..." -ForegroundColor Yellow
$null = Read-Host

Write-Success "Admin consent flow completed"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 8: Create .env file for interactive mode
# ═══════════════════════════════════════════════════════════════════════════════

Write-Info "Creating .env file for interactive auth..."

# Validate app registration before writing
if (-not $app -or -not $app.AppId) {
    Write-Fail "Cannot create .env file — app registration has no Client ID."
    Write-Fail "Please re-run the script or manually create the app registration in Azure Portal."
    exit 1
}

# Determine .env filename based on stream selection
if ($Streams -eq "All") {
    $envFileName = ".env"
    $streamLabel = "All streams (combined)"
} elseif ($selectedStreams.Count -eq 1) {
    $envFileName = ".env.stream$($selectedStreams[0])"
    $streamLabel = "Stream $($selectedStreams[0]) dedicated"
} else {
    $envFileName = ".env"
    $streamLabel = "Streams $($selectedStreams -join ',')"
}

$envContent = @"
# M365 Copilot Readiness Assessment Tool - Interactive Auth Configuration
# Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Auth Mode: Interactive Browser (delegated permissions, no secret needed)
# App Registration: $($app.DisplayName)
# Scope: $streamLabel

TENANT_ID=$($context.TenantId)
CLIENT_ID=$($app.AppId)
AUTH_MODE=interactive

# NO CLIENT_SECRET NEEDED for interactive mode
# The browser login + MFA replaces the need for a stored secret

# To use this config: copy/rename this file to .env
# DO NOT COMMIT THIS FILE TO GIT
"@

$envPath = Join-Path $PSScriptRoot $envFileName

# Check if .env already exists
if (Test-Path $envPath) {
    $existingEnv = Get-Content $envPath -Raw
    if ($existingEnv -match "CLIENT_SECRET") {
        Write-Warn "Existing .env has CLIENT_SECRET (service principal mode)"
        $overwrite = Read-Host "Overwrite with interactive auth config? (y/N)"
        if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
            # Write to .env.interactive instead
            $envPath = Join-Path $PSScriptRoot ".env.interactive"
            Write-Info "Saving to .env.interactive instead (rename to .env when ready)"
        }
    }
}

$envContent | Out-File -FilePath $envPath -Encoding UTF8 -Force
Write-Success ".env file created: $envPath"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 9: Update/Create .gitignore
# ═══════════════════════════════════════════════════════════════════════════════

$gitignorePath = Join-Path $PSScriptRoot ".gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw
    if ($gitignoreContent -notmatch "\.env") {
        Add-Content -Path $gitignorePath -Value "`n# Environment variables`n.env`n.env.*`n"
        Write-Success "Added .env to .gitignore"
    }
} else {
    @"
# Environment variables
.env
.env.*

# Python
__pycache__/
*.pyc
*.pyo

# Reports
Reports/
*.csv
"@ | Out-File -FilePath $gitignorePath -Encoding UTF8
    Write-Success "Created .gitignore"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Final Summary
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "`n=============================================================================" -ForegroundColor Green
Write-Host "   ✓ INTERACTIVE AUTH SETUP COMPLETE" -ForegroundColor Green
Write-Host "=============================================================================" -ForegroundColor Green

Write-Host "`n✓ Configuration Summary:" -ForegroundColor Green
Write-Host "  • App Registration: $($app.DisplayName)" -ForegroundColor White
Write-Host "  • Application (Client) ID: $($app.AppId)" -ForegroundColor White
Write-Host "  • Auth Type: Public Client (no secret)" -ForegroundColor White
Write-Host "  • Redirect URI: http://localhost" -ForegroundColor White
Write-Host "  • Permission Type: Delegated (user context)" -ForegroundColor White
Write-Host "  • Admin Consent: Granted" -ForegroundColor White

$streamsSummary = @()
if ($selectedStreams -contains 1) { $streamsSummary += "Graph/M365/Entra" }
if ($selectedStreams -contains 2) { $streamsSummary += "Defender" }
if ($selectedStreams -contains 3) { $streamsSummary += "Purview" }
Write-Host "  • Streams Configured: $($streamsSummary -join ', ')" -ForegroundColor White
Write-Host "  • .env File: $envPath" -ForegroundColor White

Write-Host "`nRequired User Roles (assign in Entra ID → Roles and Administrators):" -ForegroundColor Yellow
if ($selectedStreams -contains 1) {
    Write-Host "  • Stream 1 (M365/Entra): Global Reader" -ForegroundColor White
}
if ($selectedStreams -contains 2) {
    Write-Host "  • Stream 2 (Defender):   Security Reader" -ForegroundColor White
}
if ($selectedStreams -contains 3) {
    Write-Host "  • Stream 3 (Purview):    Compliance Administrator" -ForegroundColor White
}
Write-Host "  • Stream 4 (Power Platform): Power Platform Admin (no setup needed here)" -ForegroundColor Gray
Write-Host "  • Stream 5 (A365/Copilot):   GitHub access (no setup needed here)" -ForegroundColor Gray

Write-Host "`nUsage Examples:" -ForegroundColor Yellow
Write-Host "  # Run all services (user needs all roles above):" -ForegroundColor Gray
Write-Host "  python main.py --auth-mode interactive" -ForegroundColor Cyan
Write-Host ""
if ($selectedStreams -contains 1) {
    Write-Host "  # IT Admin — licensing & identity only:" -ForegroundColor Gray
    Write-Host "  python main.py --auth-mode interactive --services M365 Entra" -ForegroundColor Cyan
}
if ($selectedStreams -contains 2) {
    Write-Host "  # Security team — Defender only:" -ForegroundColor Gray
    Write-Host "  python main.py --auth-mode interactive --services Defender" -ForegroundColor Cyan
}
if ($selectedStreams -contains 3) {
    Write-Host "  # Compliance officer — Purview only:" -ForegroundColor Gray
    Write-Host "  python main.py --auth-mode interactive --services Purview" -ForegroundColor Cyan
}

Write-Host "`nHow it works:" -ForegroundColor Yellow
Write-Host "  1. Run python main.py --auth-mode interactive" -ForegroundColor White
Write-Host "  2. Browser opens → sign in with your account + MFA" -ForegroundColor White
Write-Host "  3. Token acquired → tool runs → no more prompts" -ForegroundColor White
Write-Host "  4. No secrets stored anywhere!`n" -ForegroundColor White

Write-Host "✓ Setup complete! You can now run the tool with --auth-mode interactive`n" -ForegroundColor Green

# Disconnect
Disconnect-MgGraph | Out-Null

# ═══════════════════════════════════════════════════════════════════════════════
# Step 10 (Optional): Auto-run assessment if -RunAssessment specified
# ═══════════════════════════════════════════════════════════════════════════════

if ($RunAssessment) {
    Write-Host "`n=============================================================================" -ForegroundColor Magenta
    Write-Host "   PROCESS 2: Running Assessment Automatically" -ForegroundColor Magenta
    Write-Host "=============================================================================" -ForegroundColor Magenta

    # Ensure .env is the active file (copy stream-specific if needed)
    $mainEnvPath = Join-Path $PSScriptRoot ".env"
    if ($envPath -ne $mainEnvPath) {
        Copy-Item -Path $envPath -Destination $mainEnvPath -Force
        Write-Info "Copied $envPath → .env (active config)"
    }

    # Build the --services argument based on selected streams
    $servicesArgs = @()
    if ($Streams -eq "All") {
        # No --services flag = run all
        $servicesArgs = @()
    } else {
        if ($selectedStreams -contains 1) { $servicesArgs += @("M365", "Entra") }
        if ($selectedStreams -contains 2) { $servicesArgs += @("Defender") }
        if ($selectedStreams -contains 3) { $servicesArgs += @("Purview") }
    }

    # Build command
    $pythonCmd = "py"
    $mainScript = Join-Path $PSScriptRoot "main.py"
    $baseArgs = @($mainScript, "--auth-mode", "interactive")
    if ($servicesArgs.Count -gt 0) {
        $baseArgs += @("--services") + $servicesArgs
    }

    Write-Host "`n  Running: $pythonCmd $($baseArgs -join ' ')" -ForegroundColor Cyan
    Write-Host "" 

    & $pythonCmd @baseArgs
}

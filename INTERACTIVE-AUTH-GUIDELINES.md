# Interactive Authentication — Setup & Run Guide

## What Is This?

The M365 Copilot Readiness Assessment tool can authenticate in three ways:

1. **Service Principal** (default) — headless, one app with all permissions + a secret
2. **Interactive Browser** — per-stream app registrations, delegated permissions, no secrets
3. **Device Code** — same per-stream apps as Interactive, but instead of a browser popup the tool displays a code you enter at [https://microsoft.com/devicelogin](https://microsoft.com/devicelogin). Ideal for **headless machines, remote SSH sessions, or environments where `http://localhost` is blocked**.

This guide covers **options 2 & 3: Delegated Authentication** (Interactive Browser and Device Code).

> **Key point:** Interactive and Device Code share the same app registrations, `.env` config, and setup steps. The only difference is how you authenticate at runtime (`--auth-mode interactive` vs `--auth-mode device_code`).

### How It Works

- The tool is divided into **5 streams**, each covering a different Microsoft 365 area
- Streams 1–5 each get their **own app registration** with only the permissions they need
- A tenant admin creates the 5 apps **once** and grants admin consent
- **Interactive Browser:** Users run the tool → browser opens → login with MFA → done
- **Device Code:** Users run the tool → terminal shows a code → open any browser (even on another device) → enter code → login with MFA → done
- No consent prompts at runtime (admin pre-granted)
- No client secrets to manage or rotate

### Why Per-Stream?

- **Least-privilege** — a Defender token cannot access M365 directory data
- **Role separation** — Security Reader runs Defender, Global Reader (or Compliance Administrator) runs Purview
- **Audit clarity** — each app's sign-in logs show exactly what was accessed

---

## Quick Start Flow

```mermaid
flowchart LR
    S1["STEP 1\nPrerequisites"]
    S2["STEP 2\nApp Registrations\n(Admin — one-time)"]
    S3["STEP 3\nPre-Assessment\nConfiguration"]
    S4["STEP 4\nRun"]

    S1 --> S2 --> S3 --> S4

    S4 --> M1["--auth-mode interactive\n(browser popup)"]
    S4 --> M2["--auth-mode device_code\n(enter code at URL)"]

    classDef prereq fill:#37474F,stroke:#546E7A,color:#FFF,stroke-width:2px
    classDef appreg fill:#4A148C,stroke:#7B1FA2,color:#FFF,stroke-width:2px
    classDef env fill:#E65100,stroke:#FF6D00,color:#FFF,stroke-width:2px
    classDef run fill:#1B5E20,stroke:#43A047,color:#FFF,stroke-width:2px
    classDef mode fill:#0D47A1,stroke:#1565C0,color:#FFF,stroke-width:2px

    class S1 prereq
    class S2 appreg
    class S3 env
    class S4 run
    class M1,M2 mode
```

---

## Stream Reference

```mermaid
flowchart TD
    AUTH{"Auth Mode?"}

    AUTH -->|"--auth-mode interactive"| BROWSER["Browser Login + MFA\n(popup on local machine)"]
    AUTH -->|"--auth-mode device_code"| DEVICE["Device Code Flow\n(enter code at microsoft.com/devicelogin)"]

    BROWSER --> CRED1["CLIENT_ID_STREAM1"]
    BROWSER --> CRED2["CLIENT_ID_STREAM2"]
    BROWSER --> CRED3["CLIENT_ID_STREAM3"]
    BROWSER --> CRED4["CLIENT_ID_STREAM4"]
    BROWSER --> CRED5["CLIENT_ID_STREAM5"]

    DEVICE --> CRED1
    DEVICE --> CRED2
    DEVICE --> CRED3
    DEVICE --> CRED4
    DEVICE --> CRED5

    CRED1 --> S1["Stream 1: M365 & Entra\nLicenses, Identity, Directory, Policies"]
    CRED2 --> S2["Stream 2: Defender\nThreats, Endpoints, Incidents"]
    CRED3 --> S3["Stream 3: Purview\nCompliance, DLP, Labels"]
    CRED4 --> S4["Stream 4: Power Platform\nEnvironments, DLP, AI Builder"]
    CRED5 --> S5["Stream 5: A365\nAgent Catalog"]

    S1 --> OUT["Assessment Report"]
    S2 --> OUT
    S3 --> OUT
    S4 --> OUT
    S5 --> OUT

    classDef authNode fill:#263238,stroke:#37474F,color:#FFF,stroke-width:2px
    classDef login fill:#4B0082,stroke:#6A0DAD,color:#FFF,stroke-width:2px
    classDef device fill:#BF360C,stroke:#E65100,color:#FFF,stroke-width:2px
    classDef cred fill:#0D47A1,stroke:#1565C0,color:#FFF,stroke-width:2px
    classDef s1 fill:#1565C0,stroke:#0D47A1,color:#FFF
    classDef s2 fill:#E65100,stroke:#BF360C,color:#FFF
    classDef s3 fill:#2E7D32,stroke:#1B5E20,color:#FFF
    classDef s4 fill:#6A1B9A,stroke:#4A148C,color:#FFF
    classDef s5 fill:#00695C,stroke:#004D40,color:#FFF
    classDef out fill:#1A237E,stroke:#283593,color:#FFF,stroke-width:2px

    class AUTH authNode
    class BROWSER login
    class DEVICE device
    class CRED1,CRED2,CRED3,CRED4,CRED5 cred
    class S1 s1
    class S2 s2
    class S3 s3
    class S4 s4
    class S5 s5
    class OUT out
```

| `--services` | Stream | Env Variable | User Role | What It Collects |
|---|---|---|---|---|
| `M365` / `Entra` | 1 | `CLIENT_ID_STREAM1` | Global Administrator + Global Secure Access Administrator | Licenses, Identity, Directory, Policies. `NetworkAccessPolicy.Read.All` requires the Global Secure Access Administrator directory role |
| `Defender` | 2 | `CLIENT_ID_STREAM2` | Security Reader | Threats, Endpoints, Incidents |
| `Purview` | 3 | `CLIENT_ID_STREAM3` | Global Reader  | Compliance, DLP, Labels |
| `"Power Platform"` / `"Copilot Studio"` | 4 | `CLIENT_ID_STREAM4` | Power Platform Admin | Environments, DLP, AI Builder |
| `A365` | 5 | `CLIENT_ID_STREAM5` | AI Admin or Global Admin | Agent Catalog |



---

## STEP 1: Prerequisites

- Python 3.9+
- PowerShell 7+
- Run `pip install -r requirements.txt`
- **Interactive Browser only:** Default browser available + `http://localhost` not blocked by firewall/proxy
- **Device Code:** No browser or localhost required on the machine running the tool — you can sign in from any device
- **Stream 4 (Power Platform) only:** `Az.Accounts` PowerShell module (`Install-Module Az.Accounts -Scope CurrentUser`). The Power Platform collector authenticates via `Connect-AzAccount`, which requires this module.

---

## STEP 2: Create Per-Stream App Registrations (Admin — One-Time)

**Who runs this step:** IT Admin (Global Admin or Application Administrator)

**Who does NOT run this step:** The assessment user — they only run Step 4.

---

### Option A: Automated (recommended)

Run the setup script. Each command creates the app, assigns permissions, grants admin consent, and writes the CLIENT_ID to `.env`:

```powershell
# ─── Create Stream 1 app (M365 & Entra) ───
.\setup-interactive-auth.ps1 -Streams "1"

# ─── Create Stream 2 app (Defender) ───
.\setup-interactive-auth.ps1 -Streams "2"

# ─── Create Stream 3 app (Purview) ───
.\setup-interactive-auth.ps1 -Streams "3"

# ─── Create Stream 4 app (Power Platform) ───
.\setup-interactive-auth.ps1 -Streams "4"

# ─── Create Stream 5 app (A365/Copilot) ───
.\setup-interactive-auth.ps1 -Streams "5"

# ─── Or create ALL streams at once ───
.\setup-interactive-auth.ps1

# ─── Or combine specific streams ───
.\setup-interactive-auth.ps1 -Streams "1,2"
.\setup-interactive-auth.ps1 -Streams "1,3,4"
```

**After running:** The script outputs each app's Client ID. Give these to the assessment user:

| Stream | App Name | Value to share |
|--------|----------|---------------|
| 1 | Readiness - M365 & Entra | `CLIENT_ID_STREAM1` |
| 2 | Readiness - Defender | `CLIENT_ID_STREAM2` |
| 3 | Readiness - Purview | `CLIENT_ID_STREAM3` |
| 4 | Readiness - Power Platform | `CLIENT_ID_STREAM4` |
| 5 | Readiness - A365/Copilot | `CLIENT_ID_STREAM5` |

> The admin's job ends here. The assessment user takes over at Step 3.

---

### Option B: Manual (Azure Portal) — Rare Use

<details>
<summary><strong>Click to expand manual app registration steps</strong></summary>

Go to **Azure Portal → Entra ID → App registrations → + New registration**

**Common settings for ALL apps:**

| Setting | Value |
|---------|-------|
| Supported account types | **Single tenant** |
| Redirect URI | Public client/native → `http://localhost` |
| Allow public client flows | **Yes** |

After creating each app: add the listed permissions → **Grant admin consent ✅** → copy Application (client) ID → save to `.env`.

---

**Stream 1** — `Readiness - M365 & Entra` · Role: `Global Administrator + Global Secure Access Administrator` · Save as `CLIENT_ID_STREAM1`

Microsoft Graph → Delegated: `Organization.Read.All`, `Directory.Read.All`, `User.Read.All`, `Group.Read.All`, `Application.Read.All`, `AccessReview.Read.All`, `Policy.Read.All`, `RoleManagement.Read.Directory`, `UserAuthenticationMethod.Read.All`, `Reports.Read.All`, `AuditLog.Read.All`, `Sites.Read.All`, `Files.Read.All`, `ExternalConnection.Read.All`, `Channel.ReadBasic.All`, `OnlineMeetings.Read`, `Bookings.Read.All`, `People.Read.All`, `Printer.Read.All`, `DeviceManagementManagedDevices.Read.All`, `DeviceManagementConfiguration.Read.All`, `NetworkAccessPolicy.Read.All`

> ⚠️ Do NOT add `TeamsAppInstallation.ReadWriteAndConsentSelfForChat.All` — does not exist in Graph, causes AADSTS650051.

> ⚠️ `NetworkAccessPolicy.Read.All` requires the **Global Secure Access Administrator** directory role. A Global Reader alone will receive HTTP 403 on the NetworkAccess API. If Global Secure Access is not used in your tenant, this role is optional — the tool will report it as "not activated" and continue.

---

**Stream 2** — `Readiness - Defender` · Role: `Security Reader` · Save as `CLIENT_ID_STREAM2`

- Microsoft Graph → Delegated: `SecurityEvents.Read.All`, `SecurityIncident.Read.All`, `ThreatIndicators.Read.All`, `ThreatHunting.Read.All`, `ThreatAssessment.ReadWrite.All`, `IdentityRiskyUser.Read.All`, `IdentityRiskEvent.Read.All`, `Organization.Read.All`, `Directory.Read.All`
- WindowsDefenderATP API (under "APIs my organization uses") → Delegated: `Machine.Read`
- Office 365 Management APIs (under "APIs my organization uses") → Delegated: `ActivityFeed.Read`, `ServiceHealth.Read`

---

**Stream 3** — `Readiness - Purview` · Role: `Global Reader` (minimum) · Save as `CLIENT_ID_STREAM3`

Microsoft Graph → Delegated: `InformationProtectionPolicy.Read`, `Policy.Read.All`, `Organization.Read.All`

> Global Reader covers the Graph delegated permissions. For full Purview PowerShell access (`Connect-IPPSSession` — DLP policies, sensitivity labels), assign **Compliance Administrator** (the lowest Entra role that maps to View-Only Organization Management in Purview).

---

**Stream 4** — `Readiness - Power Platform` · Role: `Power Platform Administrator` · Save as `CLIENT_ID_STREAM4`

- Microsoft Graph → Delegated: `Organization.Read.All`

> **Note:** The Stream 4 app registration only needs **Graph API** permissions. Power Platform data is collected via a separate `Connect-AzAccount` call (Az PowerShell module), which authenticates independently — it does NOT use this app registration.

> **How Stream 4 works:** Stream 4 authenticates in two steps:
> 1. **Power Platform API** — launches a PowerShell subprocess that runs `Connect-AzAccount` (from `Az.Accounts` module) to access Power Platform environments and policies
> 2. **Graph API** — uses `CLIENT_ID_STREAM4` to acquire a Graph token (for `Organization.Read.All` license queries)
>
> In **device code** mode, you will see **two separate device code prompts**. After each authentication, the tool proceeds automatically to the next step.
>
> **Prerequisites:** `Az.Accounts` PowerShell module must be installed (`Install-Module Az.Accounts -Scope CurrentUser`).

---

**Stream 5** — `Readiness - A365/Copilot` · Role: `AI Admin or Global Admin` · Save as `CLIENT_ID_STREAM5`

Microsoft Graph → Delegated: `CopilotPackages.Read.All`, `User.Read`

</details>

---

## STEP 3: Pre-Assessment Configuration

Create `.env` in the project root with only the streams you plan to run.
Each `CLIENT_ID_STREAMx` corresponds to a specific assessment stream — you only need the ones relevant to your execution:

```ini
TENANT_ID=your-tenant-id-guid
AUTH_MODE=interactive

# Only include the CLIENT_IDs for the streams you will run:
CLIENT_ID_STREAM1=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # needed for: --services M365 Entra
CLIENT_ID_STREAM2=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # needed for: --services Defender
CLIENT_ID_STREAM3=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # needed for: --services Purview
CLIENT_ID_STREAM4=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # needed for: --services "Power Platform"
CLIENT_ID_STREAM5=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # needed for: --services A365
```

For example, if you only run Defender and Purview, your `.env` only needs `CLIENT_ID_STREAM2` and `CLIENT_ID_STREAM3`.

> **Device Code note:** The `.env` is identical for both `--auth-mode interactive` and `--auth-mode device_code`. Keep `AUTH_MODE=interactive` in `.env` — the `--auth-mode device_code` CLI flag handles the switch internally.

Also set `TENANT_ID` in `params.py`:

```python
TENANT_ID = "your-tenant-id-guid"
```

> No `CLIENT_SECRET` needed — all apps are public clients (delegated auth only).

---

## STEP 4: Run the Assessment

**Who:** Assessment user (not the admin who created the apps)

The assessment user only needs:
- The `.env` file (from admin)
- The correct Entra role for their stream
- **Interactive:** A browser on the same machine
- **Device Code:** A browser on any device (phone, another PC, etc.)

### Interactive Browser (`--auth-mode interactive`)

Browser opens automatically on the local machine → login + MFA → assessment runs.

```powershell
# Stream 1: M365 + Entra — role: Global Administrator + Global Secure Access Administrator
python main.py --auth-mode interactive --services M365 Entra

# Stream 2: Defender — role: Security Reader
python main.py --auth-mode interactive --services Defender

# Stream 3: Purview — role: Global Reader (or Compliance Administrator for full PowerShell)
python main.py --auth-mode interactive --services Purview

# Stream 4: Power Platform — role: Power Platform Admin
# NOTE: Stream 4 triggers TWO auth prompts:
#   1) Connect-AzAccount (for Power Platform API access via Az.Accounts)
#   2) Graph API (for Organization.Read.All license queries)
# After each authentication, the tool proceeds automatically to the next step.
python main.py --auth-mode interactive --services "Power Platform" "Copilot Studio"

# Stream 5: A365 — role: AI Admin or Global Admin
# NOTE: Stream 5 triggers ONE auth prompt via a PowerShell subprocess
#   (Connect-MgGraph) for Copilot admin catalog access.
# After authentication, the tool proceeds automatically.
python main.py --auth-mode interactive --services A365

# All streams — requires all roles + all CLIENT_IDs
python main.py --auth-mode interactive
```

### Device Code (`--auth-mode device_code`)

Terminal displays a code → open [https://microsoft.com/devicelogin](https://microsoft.com/devicelogin) on **any device** → enter code → login with MFA → assessment runs.

Ideal for: headless VMs, remote SSH sessions, or environments where `http://localhost` is blocked.

```powershell
# Stream 1: M365 + Entra — role: Global Administrator + Global Secure Access Administrator
python main.py --auth-mode device_code --services M365 Entra

# Stream 2: Defender — role: Security Reader
python main.py --auth-mode device_code --services Defender

# Stream 3: Purview — role: Global Reader (or Compliance Administrator for full PowerShell)
python main.py --auth-mode device_code --services Purview

# Stream 4: Power Platform — role: Power Platform Admin
# NOTE: Stream 4 triggers TWO device code prompts:
#   1) Connect-AzAccount device code (for Power Platform API access via Az.Accounts)
#   2) Graph API device code (for Organization.Read.All license queries)
# After each authentication, the tool proceeds automatically to the next step.
python main.py --auth-mode device_code --services "Power Platform" "Copilot Studio"

# Stream 5: A365 — role: AI Admin or Global Admin
# NOTE: Stream 5 triggers ONE device code prompt via a PowerShell subprocess
#   (Connect-MgGraph) for Copilot admin catalog access.
# After authentication, the tool proceeds automatically.
python main.py --auth-mode device_code --services A365

# All streams — requires all roles + all CLIENT_IDs
python main.py --auth-mode device_code
```

> No consent prompts at runtime for either mode (admin pre-granted).

> **Role separation:** The admin creates apps (Step 2) and never runs the assessment. The assessment user runs the tool (Step 4) and never needs admin privileges.

---

## Comparison: Service Principal vs Interactive vs Device Code

| | Service Principal | Interactive (per-stream) | Device Code (per-stream) |
|---|---|---|---|
| `.env` | `TENANT_ID` + `CLIENT_ID` + `CLIENT_SECRET` | `TENANT_ID` + `AUTH_MODE=interactive` + `CLIENT_ID_STREAMx` | Same as Interactive |
| CLI flag | `--auth-mode service_principal` | `--auth-mode interactive` | `--auth-mode device_code` |
| Apps | 1 app (all permissions) | 1 app per stream (isolated) | Same as Interactive |
| User action | None (headless) | Browser popup + MFA | Enter code at URL + MFA |
| Browser needed | No | Yes (local machine) | Any device (phone, another PC) |
| `http://localhost` | Not required | Must be reachable | Not required |
| Security | Secret must be rotated | No secret — delegated only | No secret — delegated only |
| Best for | CI/CD, automation | Workstation with browser | Headless VM, SSH, restricted network |

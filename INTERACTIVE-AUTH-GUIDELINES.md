# Interactive Authentication — Setup & Run Guide

## What Is This?

The M365 Copilot Readiness Assessment tool can authenticate in two ways:

1. **Service Principal** (default) — headless, one app with all permissions + a secret
2. **Interactive Browser** — per-stream app registrations, delegated permissions, no secrets

This guide covers **option 2: Interactive Browser Authentication**.

### How It Works

- The tool is divided into **5 streams**, each covering a different Microsoft 365 area
- Streams 1–4 each get their **own app registration** with only the permissions they need
- Stream 5 (A365 / Copilot) authenticates via **Connect-MgGraph** (Microsoft Graph PowerShell) — no app registration needed
- A tenant admin creates the 4 apps **once** and grants admin consent
- Users run the tool → browser opens → they login with MFA → done
- No consent prompts at runtime (admin pre-granted)
- No client secrets to manage or rotate

### Why Per-Stream?

- **Least-privilege** — a Defender token cannot access M365 directory data
- **Role separation** — Security Reader runs Defender, Compliance Reader runs Purview
- **Audit clarity** — each app's sign-in logs show exactly what was accessed

---

## Quick Start Flow

```mermaid
flowchart LR
    S1["STEP 1\nPrerequisites"]
    S2["STEP 2\nApp Registrations\n(Admin — one-time)"]
    S3["STEP 3\nConfigure .env"]
    S4["STEP 4\nRun"]

    S1 --> S2 --> S3 --> S4

    classDef prereq fill:#37474F,stroke:#546E7A,color:#FFF,stroke-width:2px
    classDef appreg fill:#4A148C,stroke:#7B1FA2,color:#FFF,stroke-width:2px
    classDef env fill:#E65100,stroke:#FF6D00,color:#FFF,stroke-width:2px
    classDef run fill:#1B5E20,stroke:#43A047,color:#FFF,stroke-width:2px

    class S1 prereq
    class S2 appreg
    class S3 env
    class S4 run
```

---

## STEP 1: Prerequisites

- Python 3.9+
- PowerShell 7+
- Run `pip install -r requirements.txt`
- Default browser available (opens for login)
- `http://localhost` not blocked by firewall/proxy

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
| 5 | *(no app registration)* | Uses `Connect-MgGraph` (browser login) |

> The admin's job ends here. The assessment user takes over at Step 3.

### Option B: Manual (Azure Portal)

Go to **Azure Portal → Entra ID → App registrations → + New registration**

All apps use these common settings:

| Setting | Value |
|---------|-------|
| Supported account types | **Single tenant** |
| Redirect URI | Public client/native → `http://localhost` |
| Allow public client flows | **Yes** |

---

### Stream 1: `Readiness - M365 & Entra`

**User role required:** `Global Reader`

**Microsoft Graph → Delegated permissions:**

| Permission |
|-----------|
| `Organization.Read.All` |
| `Directory.Read.All` |
| `User.Read.All` |
| `Group.Read.All` |
| `Application.Read.All` |
| `AccessReview.Read.All` |
| `Policy.Read.All` |
| `RoleManagement.Read.Directory` |
| `UserAuthenticationMethod.Read.All` |
| `Reports.Read.All` |
| `AuditLog.Read.All` |
| `Sites.Read.All` |
| `Files.Read.All` |
| `ExternalConnection.Read.All` |
| `Channel.ReadBasic.All` |
| `OnlineMeetings.Read.All` |
| `Bookings.Read.All` |
| `People.Read.All` |
| `Printer.Read.All` |
| `DeviceManagementManagedDevices.Read.All` |
| `DeviceManagementConfiguration.Read.All` |
| `NetworkAccessPolicy.Read.All` |

**→ Grant admin consent ✅** → Copy the Application (client) ID → save as `CLIENT_ID_STREAM1`

---

### Stream 2: `Readiness - Defender`

**User role required:** `Security Reader`

**Microsoft Graph → Delegated:**

| Permission |
|-----------|
| `SecurityEvents.Read.All` |
| `SecurityIncident.Read.All` |
| `ThreatIndicators.Read.All` |
| `ThreatHunting.Read.All` |
| `ThreatAssessment.Read.All` |
| `IdentityRiskyUser.Read.All` |
| `IdentityRiskEvent.Read.All` |

**WindowsDefenderATP API** (search in "APIs my organization uses") → Delegated:

| Permission |
|-----------|
| `Machine.Read.All` |

**Office 365 Management APIs** (search in "APIs my organization uses") → Delegated:

| Permission |
|-----------|
| `ActivityFeed.Read` |
| `ServiceHealth.Read` |

**→ Grant admin consent ✅** → Copy the Application (client) ID → save as `CLIENT_ID_STREAM2`

---

### Stream 3: `Readiness - Purview`

**User role required:** `Compliance Reader`

**Microsoft Graph → Delegated:**

| Permission |
|-----------|
| `InformationProtectionPolicy.Read` |
| `Policy.Read.All` |

**→ Grant admin consent ✅** → Copy the Application (client) ID → save as `CLIENT_ID_STREAM3`

> Purview data is mainly collected via PowerShell (`Connect-IPPSSession`). This app provides supplementary Graph access.

---

### Stream 4: `Readiness - Power Platform`

**User role required:** `Power Platform Administrator`

**Power Platform API** (`https://api.bap.microsoft.com`) → Delegated:

| Permission |
|-----------|
| `user_impersonation` |

**→ Grant admin consent ✅** → Copy the Application (client) ID → save as `CLIENT_ID_STREAM4`

> Power Platform data is mainly collected via PowerShell subprocess.

---

### Stream 5: A365 / Copilot

**No app registration needed.** Uses `Connect-MgGraph` interactive browser login (falls back to device code flow).

---

## STEP 3: Configure `.env`

Create `.env` in the project root:

```ini
TENANT_ID=your-tenant-id-guid
AUTH_MODE=interactive

CLIENT_ID_STREAM1=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CLIENT_ID_STREAM2=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CLIENT_ID_STREAM3=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CLIENT_ID_STREAM4=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Also set `TENANT_ID` in `params.py`:

```python
TENANT_ID = "your-tenant-id-guid"
```

> Only configure the streams you plan to use. No `CLIENT_SECRET` needed — all apps are public clients.

---

## STEP 4: Run the Assessment

**Who:** Assessment user (not the admin who created the apps)

The assessment user only needs:
- The `.env` file (from admin)
- The correct Entra role for their stream
- A browser for login

```powershell
# Stream 1: M365 + Entra — role: Global Reader
python main.py --auth-mode interactive --services M365 Entra

# Stream 2: Defender — role: Security Reader
python main.py --auth-mode interactive --services Defender

# Stream 3: Purview — role: Compliance Reader
python main.py --auth-mode interactive --services Purview

# Stream 4: Power Platform — role: Power Platform Admin
python main.py --auth-mode interactive --services "Power Platform" "Copilot Studio"

# Stream 5: A365 — role: Global Reader + Microsoft.Graph PowerShell module
python main.py --auth-mode interactive --services A365

# All streams — requires all roles + all CLIENT_IDs
python main.py --auth-mode interactive
```

Browser opens → login + MFA → assessment runs. No consent prompts (admin pre-granted).

> **Role separation:** The admin creates apps (Step 2) and never runs the assessment. The assessment user runs the tool (Step 4) and never needs admin privileges.

---

## Stream Reference

```mermaid
flowchart TD
    LOGIN["Browser Login + MFA"]

    LOGIN --> CRED1["CLIENT_ID_STREAM1"]
    LOGIN --> CRED2["CLIENT_ID_STREAM2"]
    LOGIN --> PS["PowerShell Interactive"]

    CRED1 --> S1["Stream 1: M365 & Entra\nLicenses, Identity, Directory, Policies"]
    CRED2 --> S2["Stream 2: Defender\nThreats, Endpoints, Incidents"]
    PS --> S3["Stream 3: Purview\nCompliance, DLP, Labels"]
    PS --> S4["Stream 4: Power Platform\nEnvironments, DLP, AI Builder"]
    PS --> S5["Stream 5: A365\nAgent Catalog"]

    S1 --> OUT["Assessment Report"]
    S2 --> OUT
    S3 --> OUT
    S4 --> OUT
    S5 --> OUT

    classDef login fill:#4B0082,stroke:#6A0DAD,color:#FFF,stroke-width:2px
    classDef cred fill:#0D47A1,stroke:#1565C0,color:#FFF,stroke-width:2px
    classDef ps fill:#4E342E,stroke:#6D4C41,color:#FFF,stroke-width:2px
    classDef s1 fill:#1565C0,stroke:#0D47A1,color:#FFF
    classDef s2 fill:#E65100,stroke:#BF360C,color:#FFF
    classDef s3 fill:#2E7D32,stroke:#1B5E20,color:#FFF
    classDef s4 fill:#6A1B9A,stroke:#4A148C,color:#FFF
    classDef s5 fill:#00695C,stroke:#004D40,color:#FFF
    classDef out fill:#1A237E,stroke:#283593,color:#FFF,stroke-width:2px

    class LOGIN login
    class CRED1,CRED2 cred
    class PS ps
    class S1 s1
    class S2 s2
    class S3 s3
    class S4 s4
    class S5 s5
    class OUT out
```

| `--services` | Stream | Env Variable | User Role |
|---|---|---|---|
| `M365` / `Entra` | 1 | `CLIENT_ID_STREAM1` | Global Reader |
| `Defender` | 2 | `CLIENT_ID_STREAM2` | Security Reader |
| `Purview` | 3 | `CLIENT_ID_STREAM3` | Compliance Reader |
| `"Power Platform"` / `"Copilot Studio"` | 4 | `CLIENT_ID_STREAM4` | Power Platform Admin |
| `A365` | 5 | *(none — uses `Connect-MgGraph`)* | Global Reader |

---

## Comparison: Service Principal vs Interactive

| | Service Principal | Interactive (per-stream) |
|---|---|---|
| `.env` | `TENANT_ID` + `CLIENT_ID` + `CLIENT_SECRET` | `TENANT_ID` + `AUTH_MODE=interactive` + `CLIENT_ID_STREAMx` |
| Apps | 1 app (all permissions) | 1 app per stream (isolated) |
| User action | None (headless) | Browser login + MFA |
| Security | Secret must be rotated | No secret — delegated only |

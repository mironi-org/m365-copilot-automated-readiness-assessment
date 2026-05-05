# Execution Guidelines: Interactive Browser Authentication

This document provides operational guidance for running the M365 Copilot Readiness Assessment tool using **interactive browser authentication** (`InteractiveBrowserCredential`) instead of a service principal. It covers the 5 API stream architecture, per-stream permission requirements, multi-user execution scenarios, and all prerequisites needed before first run — including app registration setup (automated or manual), delegated permission configuration, admin consent, and role assignments.

For the technical implementation plan (code changes, file modifications, backup strategy), see [`IMPLEMENTATION_PLAN_interactive_auth.md`](IMPLEMENTATION_PLAN_interactive_auth.md).

---

## Stream-Based Execution by User Permissions

### Architecture: 5 API Streams

The tool accesses 5 independent API streams. Each stream requires **different permissions** and can be run by **different users**:

```mermaid
flowchart TD
    %% Authentication Layer
    LOGIN["🔐 Browser Login + MFA"]

    %% Auth Method Router
    LOGIN --> AUTH_PYTHON["Python InteractiveBrowserCredential"]
    LOGIN --> AUTH_PS["PowerShell Interactive"]
    LOGIN --> AUTH_DC["Device Code Flow"]

    %% Streams
    subgraph STREAMS[" "]
        direction LR

        subgraph S1["STREAM 1 — Graph"]
            S1_CMD["--services M365 Entra"]
            S1_DATA["Licenses · Identity · Directory"]
            S1_ROLE["Role: Global Reader"]
        end

        subgraph S2["STREAM 2 — Defender"]
            S2_CMD["--services Defender"]
            S2_DATA["Threats · Endpoints · Posture"]
            S2_ROLE["Role: Security Reader"]
        end

        subgraph S3["STREAM 3 — Purview"]
            S3_CMD["--services Purview"]
            S3_DATA["Compliance · DLP Policies"]
            S3_ROLE["Role: Compliance Reader"]
        end

        subgraph S4["STREAM 4 — Power Platform"]
            S4_CMD["--services Power Platform"]
            S4_DATA["Environments · DLP · AI Builder"]
            S4_ROLE["Role: Power Platform Admin"]
        end

        subgraph S5["STREAM 5 — Copilot"]
            S5_CMD["--services A365"]
            S5_DATA["Agent Catalog · Details"]
            S5_ROLE["Role: GitHub Copilot Access"]
        end
    end

    %% Connections
    AUTH_PYTHON ==> S1_CMD
    AUTH_PYTHON ==> S2_CMD
    AUTH_PS -.-> S3_CMD
    AUTH_PS -.-> S4_CMD
    AUTH_DC -.-> S5_CMD

    %% Output
    S1_ROLE --> REPORT["📊 Assessment Report"]
    S2_ROLE --> REPORT
    S3_ROLE --> REPORT
    S4_ROLE --> REPORT
    S5_ROLE --> REPORT

    %% Styling
    classDef loginStyle fill:#4B0082,stroke:#6A0DAD,color:#FFF,stroke-width:2px
    classDef pythonAuth fill:#0D47A1,stroke:#1565C0,color:#FFF,stroke-width:2px
    classDef psAuth fill:#4E342E,stroke:#6D4C41,color:#FFF,stroke-width:2px
    classDef dcAuth fill:#1B5E20,stroke:#2E7D32,color:#FFF,stroke-width:2px
    classDef stream1 fill:#1565C0,stroke:#0D47A1,color:#FFF
    classDef stream2 fill:#E65100,stroke:#BF360C,color:#FFF
    classDef stream3 fill:#2E7D32,stroke:#1B5E20,color:#FFF
    classDef stream4 fill:#6A1B9A,stroke:#4A148C,color:#FFF
    classDef stream5 fill:#00695C,stroke:#004D40,color:#FFF
    classDef reportStyle fill:#1A237E,stroke:#283593,color:#FFF,stroke-width:2px

    class LOGIN loginStyle
    class AUTH_PYTHON pythonAuth
    class AUTH_PS psAuth
    class AUTH_DC dcAuth
    class S1_CMD,S1_DATA,S1_ROLE stream1
    class S2_CMD,S2_DATA,S2_ROLE stream2
    class S3_CMD,S3_DATA,S3_ROLE stream3
    class S4_CMD,S4_DATA,S4_ROLE stream4
    class S5_CMD,S5_DATA,S5_ROLE stream5
    class REPORT reportStyle
```

### Stream-to-Permission Mapping

| Stream | `--services` Value | Minimum Entra Role | Scenario | Delegated Permissions Required |
|--------|-------------------|-------------------|----------|-------------------------------|
| **1. Graph** | `M365 Entra` | Global Reader | **C** — IT Admin | `User.Read.All`, `Directory.Read.All`, `Organization.Read.All`, `Reports.Read.All`, `AuditLog.Read.All`, `Sites.Read.All`, `Files.Read.All`, `ExternalConnection.Read.All`, `Channel.ReadBasic.All`, `OnlineMeetings.Read.All`, `Bookings.Read.All`, `People.Read.All`, `Printer.Read.All`, `Policy.Read.All`, `RoleManagement.Read.Directory`, `UserAuthenticationMethod.Read.All`, `AccessReview.Read.All`, `Application.Read.All`, `DeviceManagementManagedDevices.Read.All`, `DeviceManagementConfiguration.Read.All`, `NetworkAccessPolicy.Read.All` |
| **2. Defender** | `Defender` | Security Reader | **B** — Security team | `SecurityEvents.Read.All`, `SecurityIncident.Read.All`, `ThreatIndicators.Read.All`, `ThreatHunting.Read.All`, `ThreatAssessment.Read.All`, `IdentityRiskyUser.Read.All`, `IdentityRiskEvent.Read.All` + Defender API: `Machine.Read.All` |
| **3. Purview** | `Purview` | Compliance Reader | **D** — Compliance officer | `InformationProtectionPolicy.Read` + Exchange Online PowerShell access (handled via `Connect-IPPSSession`) |
| **4. Power Platform** | `"Power Platform" "Copilot Studio"` | Power Platform Admin | **E** — Power Platform admin | Handled via PowerShell interactive login (separate from Graph) |
| **5. Copilot/A365** | `A365` | N/A (GitHub) | **F** — Developer Lead | `User.Read`, `Directory.Read.All`, `CopilotPackages.Read.All` via `Connect-MgGraph` |

### Multi-User Execution Scenarios

**Scenario A: One user with all permissions (simplest)**
```powershell
python main.py --auth-mode interactive
# User must have: Global Reader + Security Reader + Compliance Reader
```

**Scenario B: Security team runs Defender only**
```powershell
python main.py --auth-mode interactive --services Defender
# User only needs: Security Reader role
# Delegated permissions: SecurityEvents.Read.All, ThreatHunting.Read.All, etc.
```

**Scenario C: IT Admin runs licensing/identity checks**
```powershell
python main.py --auth-mode interactive --services M365 Entra
# User only needs: Global Reader role
# Delegated permissions: User.Read.All, Directory.Read.All, Reports.Read.All, etc.
```

**Scenario D: Compliance officer runs Purview**
```powershell
python main.py --auth-mode interactive --services Purview
# User only needs: Compliance Reader / Compliance Admin
# Auth handled by PowerShell Connect-IPPSSession (already interactive)
```

**Scenario E: Power Platform admin runs Power Platform + Copilot Studio**
```powershell
python main.py --auth-mode interactive --services "Power Platform" "Copilot Studio"
# User only needs: Power Platform Admin / Environment Admin
# Auth handled by PowerShell interactive login (already interactive)
```

**Scenario F: Combined results from multiple users**
Each user runs their stream independently. Results export to separate files that can be combined.

### Design Decision: Token Scope Strategy

When `--auth-mode interactive` is used, the `InteractiveBrowserCredential` requests the `.default` scope for each API resource. This returns all delegated permissions that were admin-consented on the app registration — no per-stream scope filtering is needed.

| Services Selected | Scope Requested | Notes |
|---|---|---|
| `M365 Entra` | `https://graph.microsoft.com/.default` | All consented Graph delegated permissions |
| `Defender` | `https://graph.microsoft.com/.default` + `https://api.securitycenter.microsoft.com/.default` | Graph + Defender API |
| `Purview` | Minimal (PowerShell handles its own auth) | No Python credential used |
| `"Power Platform" "Copilot Studio"` | Minimal (PowerShell handles its own auth) | No Python credential used |
| `A365` | Minimal (PowerShell `Connect-MgGraph` handles its own auth) | No Python credential used |
| All (no `--services` flag) | All resource scopes as needed |  |

> **Note**: Streams 3, 4, and 5 already use interactive user auth via PowerShell subprocesses — the `InteractiveBrowserCredential` change only affects Streams 1 and 2 (Graph + Defender).

---

## Two-Process Workflow

The interactive auth workflow is split into **two independent processes**. Process 1 can be done once by an admin; Process 2 is repeated by anyone running assessments.

```mermaid
flowchart LR
    %% Process 1: Setup
    subgraph P1["⚙️ PROCESS 1: App Registration"]
        direction TB
        P1_Q{"Setup Method?"}
        P1_A["A: Script\n.\setup-interactive-auth.ps1"]
        P1_B["B: Manual Portal\n+ edit .env"]
        P1_C["C: Script + Run\n-RunAssessment flag"]
        P1_ENV[".env file ready"]

        P1_Q -->|"Automated"| P1_A --> P1_ENV
        P1_Q -->|"Manual"| P1_B --> P1_ENV
        P1_Q -->|"End-to-End"| P1_C
    end

    %% Process 2: Run
    subgraph P2["▶️ PROCESS 2: Run Assessment"]
        direction TB
        P2_CMD["python main.py\n--auth-mode interactive\n--services ..."]
        P2_AUTH["Browser Login + MFA"]
        P2_OUT["📊 Report"]

        P2_CMD --> P2_AUTH --> P2_OUT
    end

    %% Connections between processes
    P1_ENV ==>|"Copy .env.streamX → .env"| P2_CMD
    P1_C ==>|"Auto-launches"| P2_CMD

    %% Styling
    classDef setupStyle fill:#1A237E,stroke:#3949AB,color:#FFF,stroke-width:2px
    classDef runStyle fill:#1B5E20,stroke:#43A047,color:#FFF,stroke-width:2px
    classDef choiceStyle fill:#B71C1C,stroke:#E53935,color:#FFF,stroke-width:2px
    classDef envStyle fill:#E65100,stroke:#FF6D00,color:#FFF,stroke-width:2px
    classDef cmdStyle fill:#004D40,stroke:#00897B,color:#FFF,stroke-width:2px
    classDef reportStyle fill:#4A148C,stroke:#7B1FA2,color:#FFF,stroke-width:2px

    class P1_Q choiceStyle
    class P1_A,P1_B setupStyle
    class P1_C cmdStyle
    class P1_ENV envStyle
    class P2_CMD,P2_AUTH runStyle
    class P2_OUT reportStyle
```

### Process 1: App Registration Setup (One-Time)

Choose **one** of these approaches:

| Approach | When to Use | Result |
|----------|-------------|--------|
| **A. Setup script** | You have PowerShell + Global Admin access | Script creates app + writes `.env.streamX` automatically |
| **B. Manual portal + edit `.env`** | App already exists, or different team created it | You just need the CLIENT_ID from portal |
| **C. Both together** | Want to create app AND run assessment in one shot | Script + auto-run |

#### Approach A: Automated Script

```powershell
.\setup-interactive-auth.ps1 -Streams "1"   # Creates app + .env.stream1
Copy-Item .env.stream1 .env                  # Activate for use
```

#### Approach B: Manual (Edit `.env` Directly)

If the app registration was created manually or by another process:

1. Get the **Application (client) ID** from Azure Portal → Entra ID → App registrations
2. Get the **Tenant ID** from Azure Portal → Entra ID → Overview
3. Create/edit `.env` in the project root:

```ini
TENANT_ID=your-tenant-id-here
CLIENT_ID=your-client-id-here
AUTH_MODE=interactive
```

That's it. No script needed. Ensure the app registration has:
- Platform: "Mobile and desktop applications" with redirect URI `http://localhost`
- "Allow public client flows" = Yes
- Delegated permissions granted + admin consent (see permissions tables below)

#### Approach C: Setup + Run Together (End-to-End Automation)

Use `-RunAssessment` to execute both processes in one command:

```powershell
# Create Stream 1 app registration AND immediately run the assessment
.\setup-interactive-auth.ps1 -Streams "1" -RunAssessment

# Create combined app AND run all streams
.\setup-interactive-auth.ps1 -RunAssessment

# Create Stream 2 app AND run Defender assessment
.\setup-interactive-auth.ps1 -Streams "2" -RunAssessment
```

The script will:
1. Create the app registration + configure permissions + get admin consent
2. Write the `.env` file
3. Copy it to active `.env` (if stream-specific)
4. Launch `python main.py --auth-mode interactive --services ...` automatically

### Process 2: Run Assessment by Stream

Once `.env` is configured (from either approach above), run the assessment:

```powershell
# Stream 1: M365 + Entra (Graph API)
python main.py --auth-mode interactive --services M365 Entra

# Stream 2: Defender
python main.py --auth-mode interactive --services Defender

# Stream 3: Purview (PowerShell auth — .env CLIENT_ID not used)
python main.py --auth-mode interactive --services Purview

# Stream 4: Power Platform (PowerShell auth — .env CLIENT_ID not used)
python main.py --auth-mode interactive --services "Power Platform" "Copilot Studio"

# Stream 5: Copilot/A365 (device code — .env CLIENT_ID not used)
python main.py --auth-mode interactive --services A365

# All streams at once
python main.py --auth-mode interactive
```

> **Note**: Only Streams 1 and 2 use the Python `InteractiveBrowserCredential` (and thus need CLIENT_ID in `.env`). Streams 3-5 authenticate via PowerShell subprocesses with their own interactive login prompts.

---

## Usage After Implementation

```powershell
# Service principal (unchanged, default)
python main.py --services M365 Entra Defender

# Interactive browser auth (new) — all services
python main.py --auth-mode interactive

# Interactive — specific stream by permission level
python main.py --auth-mode interactive --services M365 Entra
python main.py --auth-mode interactive --services Defender
python main.py --auth-mode interactive --services Purview
python main.py --auth-mode interactive --services "Power Platform" "Copilot Studio"
python main.py --auth-mode interactive --services A365
```

### `.env` for interactive mode

**Single app (all streams combined):**
```
TENANT_ID=your-tenant-id
CLIENT_ID=your-app-registration-id
AUTH_MODE=interactive
```

**Dedicated app per stream (strict isolation):**

The setup script creates stream-specific `.env` files when run per-stream:
```powershell
.\setup-interactive-auth.ps1 -Streams "1"   # Creates .env.stream1
.\setup-interactive-auth.ps1 -Streams "2"   # Creates .env.stream2
```

Each team copies their stream file to `.env` before running:
```powershell
# IT Admin uses Stream 1 app:
Copy-Item .env.stream1 .env
python main.py --auth-mode interactive --services M365 Entra

# Security team uses Stream 2 app:
Copy-Item .env.stream2 .env
python main.py --auth-mode interactive --services Defender
```

| File | App Registration | Permissions |
|------|-----------------|-------------|
| `.env.stream1` | "M365 Copilot Readiness - Stream 1 (Graph)" | Stream 1 delegated only |
| `.env.stream2` | "M365 Copilot Readiness - Stream 2 (Defender)" | Stream 2 delegated only |
| `.env` (from `-Streams "All"`) | "M365 Copilot Readiness - Interactive Auth" | All streams combined |

---

## Prerequisites for Interactive Browser Mode

### A. Azure AD App Registration Setup

#### Option 1: Automated Setup (Recommended)

Run the provided script to create the app registration, configure delegated permissions per stream, grant admin consent, and generate the `.env` file — all in one step:

```powershell
# All streams (default — Graph + Defender + Purview)
.\setup-interactive-auth.ps1

# Only specific streams (least-privilege per team)
.\setup-interactive-auth.ps1 -Streams "1,2"    # IT Admin + Security
.\setup-interactive-auth.ps1 -Streams "2"      # Security team only
.\setup-interactive-auth.ps1 -Streams "1"      # IT Admin only
.\setup-interactive-auth.ps1 -Streams "3"      # Compliance only
```

The script:
- Creates a **public client** app registration (no secret)
- Sets redirect URI `http://localhost` and enables public client flows
- Adds **delegated** permissions (not application) for selected streams
- Detects Defender/O365 Management API availability in the tenant
- Opens browser for admin consent
- Writes `.env` with `AUTH_MODE=interactive`

> **Requires:** Global Administrator or Application Administrator role to run.

#### Option 2: Manual Setup (Portal)

1. **Create or modify an App Registration** in Azure Portal → Entra ID → App registrations
2. **Authentication settings:**
   - Platform: "Mobile and desktop applications"
   - Redirect URI: `http://localhost`
   - Toggle **"Allow public client flows"** = **Yes**
3. **No client secret needed** — delete existing secret if desired (not required)
4. Note down the **Application (client) ID** — this goes in `.env` as `CLIENT_ID`
5. Add delegated permissions per stream (see Section B below)
6. Grant admin consent

### B. Delegated Permissions by Stream

Add **only the permissions needed for the streams your user will run**. Grant admin consent per stream.

#### How to Add Delegated Permissions (Portal Step-by-Step)

**Navigate to:**
> Azure Portal → **Microsoft Entra ID** → **App registrations** → *[your app (CLIENT_ID)]* → **API permissions**

**Steps:**

1. Click **"+ Add a permission"**
2. Select the target API:
   - **For Stream 1 & Stream 2 (Graph permissions):** Choose **"Microsoft Graph"** → **"Delegated permissions"** → search & check each permission from the tables below
   - **For Stream 2 (Defender API):** Choose **"APIs my organization uses"** → search `WindowsDefenderATP` (or paste `fc780465-2017-40d4-a0c5-307022471b92`) → **"Delegated permissions"** → check `Machine.Read.All`
   - **For Stream 2 (O365 Management API):** Choose **"APIs my organization uses"** → search `Office 365 Management APIs` (or paste `c5393580-f805-4401-95e8-94b7a6ef2fc2`) → **"Delegated permissions"** → check `ActivityFeed.Read`, `ServiceHealth.Read`
   - **For Stream 3 (Purview):** Choose **"Microsoft Graph"** → **"Delegated permissions"** → check `InformationProtectionPolicy.Read`
3. Click **"Add permissions"**
4. Click **"Grant admin consent for [your tenant]"** (requires Global Admin)
5. Verify green checkmarks ✅ appear next to each permission

**Per-Stream Strategy:**

| Approach | When to Use |
|----------|-------------|
| Add all permissions at once | One admin runs all streams |
| Add per-stream permissions only | Different admins run different streams (least-privilege) |
| Separate app registrations per stream | Strict isolation between teams (advanced) |

> **Important:** Even if all permissions are consented on the app, the signed-in user can only access data their **Entra ID role** allows. Permissions + Role = Access.

---

#### Stream 1: Microsoft Graph (M365 + Entra) — User Role: Global Reader

| Permission | Purpose |
|-----------|---------|
| `User.Read.All` | Read all user profiles |
| `Directory.Read.All` | Read directory data |
| `Organization.Read.All` | Read organization info |
| `Policy.Read.All` | Read all policies |
| `RoleManagement.Read.Directory` | Read directory role assignments |
| `UserAuthenticationMethod.Read.All` | Read auth methods |
| `AccessReview.Read.All` | Read access reviews |
| `DeviceManagementManagedDevices.Read.All` | Read managed devices |
| `DeviceManagementConfiguration.Read.All` | Read device config |
| `NetworkAccessPolicy.Read.All` | Read network access policies |
| `Application.Read.All` | Read app registrations |
| `AuditLog.Read.All` | Read audit logs |
| `Reports.Read.All` | Read usage reports |
| `Sites.Read.All` | Read SharePoint sites |
| `Files.Read.All` | Read files |
| `ExternalConnection.Read.All` | Read Graph connectors |
| `Channel.ReadBasic.All` | Read Teams channels |
| `OnlineMeetings.Read.All` | Read meetings |
| `Bookings.Read.All` | Read bookings data |
| `People.Read.All` | Read people data |
| `Printer.Read.All` | Read printer data |
| `WorkplaceAnalytics-Reports.Read.All` | Read workplace analytics |

#### Stream 2: Defender — User Role: Security Reader

**Microsoft Graph delegated permissions:**

| Permission | Purpose |
|-----------|---------|
| `SecurityEvents.Read.All` | Read security events |
| `SecurityIncident.Read.All` | Read security incidents |
| `ThreatIndicators.Read.All` | Read threat indicators |
| `ThreatHunting.Read.All` | Read threat hunting data |
| `ThreatAssessment.Read.All` | Read threat assessments |
| `IdentityRiskyUser.Read.All` | Read risky user data |
| `IdentityRiskEvent.Read.All` | Read risk events |

**Defender for Endpoint API** (Resource: `fc780465-2017-40d4-a0c5-307022471b92`):

| Permission | Purpose |
|-----------|---------|
| `Machine.Read.All` | Read device/machine info from Defender |

**Office 365 Management API** (Resource: `c5393580-f805-4401-95e8-94b7a6ef2fc2`):

| Permission | Purpose |
|-----------|---------|
| `ActivityFeed.Read` | Read activity feed (Copilot telemetry) |
| `ServiceHealth.Read` | Read service health data |

#### Stream 3: Purview — User Role: Compliance Reader / Compliance Admin

| Permission | Purpose |
|-----------|---------|
| `InformationProtectionPolicy.Read` | Read info protection policies |

> **Note**: Purview primarily authenticates via PowerShell `Connect-IPPSSession` (interactive login). Only minimal Graph permissions needed.

#### Stream 4: Power Platform + Copilot Studio — User Role: Power Platform Admin

> No additional Graph delegated permissions required. Authentication is handled entirely via PowerShell interactive login subprocess.

#### Stream 5: A365 (Copilot Admin) — User Role: GitHub access

> No additional Graph delegated permissions required via this app registration. Authentication is handled via `Connect-MgGraph` device code flow in PowerShell with scopes: `User.Read`, `Directory.Read.All`, `CopilotPackages.Read.All`.

### C. Admin Consent

A **Global Admin** must grant consent. Options:

| Approach | When to Use |
|----------|-------------|
| Grant all permissions at once | Single user runs all streams |
| Grant per-stream permissions | Different users run different streams — consent only what each needs |

Azure Portal → App Registration → API Permissions → **"Grant admin consent for [tenant]"**

### D. User Role Assignments (per stream)

| Stream | Required Entra ID Role | Who Typically Has It |
|--------|----------------------|---------------------|
| 1. Graph (M365/Entra) | **Global Reader** | IT Admin, M365 Admin |
| 2. Defender | **Security Reader** | SOC Analyst, Security Admin |
| 3. Purview | **Compliance Reader** or **Compliance Admin** | Compliance Officer |
| 4. Power Platform | **Power Platform Admin** or Environment Admin | Power Platform Admin |
| 5. A365 | GitHub Copilot license + directory access | Developer Lead |

### E. Local Machine Requirements

| Requirement | Detail |
|-------------|--------|
| Python 3.9+ | Already required by this tool |
| `azure-identity` package | Already in `requirements.txt` |
| Web browser | Default browser will open for login |
| Network access | `http://localhost` must not be blocked by firewall |
| No proxy interference | Localhost redirect must reach back to Python process |
| PowerShell 7+ | Required for Streams 3, 4, 5 (already a tool prerequisite) |

### F. `.env` File Configuration

```ini
TENANT_ID=your-tenant-id
CLIENT_ID=your-app-registration-client-id
AUTH_MODE=interactive
# CLIENT_SECRET is NOT needed for interactive mode
```

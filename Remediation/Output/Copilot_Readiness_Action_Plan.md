# Microsoft 365 Copilot Readiness - Detailed Action Plan

**Generated:** May 24, 2026  
**Total Action Items:** 25  
**Source:** M365 Copilot Readiness Assessment  
**Methodology:** Step 2 — Row-by-Row Implementation Guide

## Priority Breakdown

| Priority | Count | Target Timeline |
|----------|-------|-----------------|
| 🟠 High | 3 | 30 days |
| 🟡 Medium | 19 | 90 days |
| 🟢 Low | 3 | 120 days |

## Table of Contents


### 🟠 High Priority

- [1. Microsoft Kaizala](#1-microsoft-kaizala)
- [2. SharePoint Content Deployment](#2-sharepoint-content-deployment)
- [3. Microsoft Entra ID P1](#3-microsoft-entra-id-p1)

### 🟡 Medium Priority

- [4. Microsoft Loop](#4-microsoft-loop)
- [5. Microsoft Stream for Office 365 (E5)](#5-microsoft-stream-for-office-365-e5)
- [6. Clipchamp](#6-clipchamp)
- [7. Yammer Enterprise](#7-yammer-enterprise)
- [8. Whiteboard (Plan 3)](#8-whiteboard-plan-3)
- [9. Viva Engage Core](#9-viva-engage-core)
- [10. Microsoft Intune for Office 365](#10-microsoft-intune-for-office-365)
- [11. Microsoft Forms (Plan E5)](#11-microsoft-forms-plan-e5)
- [12. Viva Insights - MyAnalytics (Full)](#12-viva-insights---myanalytics-full)
- [13. Exchange Online (Plan 2) - Activity Baseline](#13-exchange-online-plan-2---activity-baseline)
- [14. Microsoft Entra ID P2](#14-microsoft-entra-id-p2)
- [15. Microsoft Entra ID P2](#15-microsoft-entra-id-p2)
- [16. Microsoft Entra ID P2](#16-microsoft-entra-id-p2)
- [17. Microsoft Entra ID P2](#17-microsoft-entra-id-p2)
- [18. Microsoft Entra ID P1](#18-microsoft-entra-id-p1)
- [19. Microsoft Entra ID P1](#19-microsoft-entra-id-p1)
- [20. Microsoft Entra ID P1](#20-microsoft-entra-id-p1)
- [21. Microsoft Entra Internet Access](#21-microsoft-entra-internet-access)
- [22. Microsoft Entra Private Access](#22-microsoft-entra-private-access)

### 🟢 Low Priority

- [23. Microsoft Places (Core)](#23-microsoft-places-core)
- [24. Microsoft Entra Internet Access](#24-microsoft-entra-internet-access)
- [25. Microsoft Entra Private Access](#25-microsoft-entra-private-access)

---

## 1. Microsoft Kaizala

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟠 High |
| **Status** | Insight |

### Current Situation

> Limited Teams presence: only 0 Teams users. Kaizala migration requires concurrent Teams adoption strategy for frontline workers.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Plan comprehensive migration combining Kaizala sunset with Teams frontline deployment. Focus on mobile-first training, shift handoff workflows, and walkie-talkie features to ease transition for deskless workers.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Plan Frontline Migration](https://learn.microsoft.com/microsoft-365/frontline/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 2. SharePoint Content Deployment

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟠 High |
| **Status** | Warning |

### Current Situation

> ZERO SharePoint sites deployed - Copilot has no organizational content to access

**Why this matters for Copilot:** SharePoint content is the primary knowledge base for Microsoft 365 Copilot. Without properly structured and indexed content in SharePoint, Copilot lacks the organizational knowledge to generate relevant, accurate responses for users.

### Recommended Action

URGENT: Deploy SharePoint sites and migrate content immediately. Without SharePoint content, Copilot cannot provide value based on organizational knowledge. Start by creating sites for key departments, projects, and knowledge areas. Migrate critical documents from file shares, network drives, and email attachments to SharePoint. Upload policies, procedures, templates, and institutional knowledge. Copilot's effectiveness depends entirely on accessible content - zero sites means zero organizational intelligence.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Telemetry Partial |
| **False Positive Risk** | High |
| **False Negative Risk** | High |
| **Confidence Level** | Low |
| **Impact if Not Addressed** | High — insufficient content limits Copilot knowledge base |

### Step-by-Step Implementation

1. Assess current SharePoint environment: Navigate to [SharePoint admin center](https://admin.microsoft.com/sharepoint) → Active sites
2. Identify content sources for migration: file shares, network drives, legacy platforms, local documents
3. Plan site architecture: Create departmental/project sites with clear naming conventions and proper structure
4. Create sites: SharePoint admin center → Sites → Active sites → + Create (choose Team site or Communication site)
5. Configure site settings: Permissions model (private/public), sharing policies, storage quotas
6. Use SharePoint Migration Tool (SPMT) or Migration Manager for bulk content migration from file shares
7. Apply metadata, content types, and managed columns to migrated content for Copilot discoverability
8. Configure governance: Apply sensitivity labels, retention policies, and DLP rules to sites/libraries
9. Ensure minimum 100+ documents are properly indexed — verify via SharePoint search works correctly
10. Validate Copilot can search and reference migrated content: Test with Copilot prompts about uploaded docs
11. Create training materials and conduct user adoption sessions for content owners and editors
12. Set up usage metrics tracking: SharePoint admin center → Reports → Site usage

### Reference Documentation

- [Get Started with SharePoint](https://learn.microsoft.com/sharepoint/get-started)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] 3-5 SharePoint sites created with proper structure and permissions
- [ ] Content migrated from legacy sources with intact metadata
- [ ] 100+ documents indexed and searchable via SharePoint search
- [ ] Copilot can search and reference migrated content accurately
- [ ] Sensitivity labels and governance policies applied
- [ ] User training completed for content owners and editors
- [ ] Usage metrics showing active engagement post-migration

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 3. Microsoft Entra ID P1

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟠 High |
| **Status** | Action Required |

### Current Situation

> Only 4 of 37 users (10.8%) enrolled in MFA, exposing Copilot to credential theft

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Enforce MFA registration for all users accessing Copilot. Use Conditional Access to require MFA for Microsoft 365 apps. Compromised accounts without MFA can access Copilot to exfiltrate organizational data through AI prompts. Aim for 100% MFA coverage.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Configure MFA Requirements](https://learn.microsoft.com/entra/identity/authentication/howto-mfa-getstarted)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 4. Microsoft Loop

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Limited collaboration detected with 0 SharePoint sites and 0 Teams meetings. Microsoft Loop with Copilot can transform team collaboration patterns.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Launch Microsoft Loop training program to establish collaborative work culture with Copilot-powered canvases for ideation and project planning.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Collaborate with Copilot in Loop](https://learn.microsoft.com/microsoft-loop/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 5. Microsoft Stream for Office 365 (E5)

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Limited meeting volume of 0 Teams meetings. Stream can establish video-based knowledge capture culture that Copilot makes searchable and actionable.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Launch training video initiative using Stream with AI transcription. Create searchable video library for onboarding, product demos, and how-to content that Copilot can surface contextually.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Intelligent Video with Stream](https://learn.microsoft.com/stream/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 6. Clipchamp

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Limited meeting activity with 0 Teams meetings. Clipchamp with Copilot can help establish video-based communication culture - AI-powered video editing makes creating polished recordings accessible to all users.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Launch Clipchamp training for creating video announcements, how-to guides, and product demos. Video content drives engagement in hybrid work - start with executive updates and employee onboarding materials.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [AI-Assisted Video Creation](https://learn.microsoft.com/clipchamp/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 7. Yammer Enterprise

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Smaller user base of 0 active M365 users. Yammer communities can establish peer-learning culture essential for AI adoption.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Create focused Yammer community with weekly Copilot tips from power users. In smaller organizations, social knowledge transfer accelerates AI proficiency.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Build Communities in Yammer](https://learn.microsoft.com/yammer/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 8. Whiteboard (Plan 3)

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Limited meeting collaboration with 0 Teams meetings (0.0 avg per user). Whiteboard with Copilot can establish visual brainstorming culture.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Launch Whiteboard training program with Copilot-assisted templates for innovation workshops, sprint planning, and retrospectives. Visual collaboration with AI assistance can increase engagement and creativity in hybrid work environments.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Copilot in Whiteboard](https://learn.microsoft.com/microsoft-365/whiteboard/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 9. Viva Engage Core

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Smaller user base of 0 active M365 users. Viva Engage can establish knowledge-sharing culture critical for Copilot adoption at scale - agents need organizational knowledge graph built through community discussions.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Launch focused Viva Engage community with weekly Copilot tips from power users. In smaller organizations, personal knowledge transfer through social platforms accelerates AI proficiency faster than formal training alone.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Build Copilot Communities in Viva Engage](https://learn.microsoft.com/viva/engage/overview)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 10. Microsoft Intune for Office 365

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | PendingActivation |

### Current Situation

> Microsoft Intune for Office 365 is PendingActivation in O365 w/o Teams Bundle M5, lacking mobile app protection for Copilot on phones/tablets

**Why this matters for Copilot:** Device compliance policies ensure that only secure, managed devices can access Copilot. Without Intune enforcement, sensitive data processed by Copilot may be accessible from non-compliant or compromised devices.

### Recommended Action

Enable Microsoft Intune for Office 365 to protect Copilot data on mobile devices (phones and tablets). Without mobile app management, users accessing Copilot on mobile devices can: 1) Copy/paste AI-generated summaries containing sensitive data to personal apps, 2) Take screenshots of Copilot responses without DLP enforcement, 3) Store Office files with Copilot content on unencrypted devices, 4) Access Copilot from jailbroken/rooted devices bypassing security. Configure Mobile Application Management (MAM) policies for Office apps to: require app PIN for Copilot access, prevent copy/paste and screenshots, encrypt app data at rest, block managed apps on non-compliant devices. Available in Business Basic/Standard tiers - provides essential mobile protection without full Intune licensing. Start with protecting Outlook, Teams, and OneDrive mobile apps where Copilot is integrated.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Permission Blocked |
| **False Positive Risk** | High |
| **False Negative Risk** | Medium |
| **Confidence Level** | Low |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Navigate to [Microsoft Intune admin center](https://intune.microsoft.com) → Devices → Enrollment
2. Configure enrollment restrictions: Define which device types and platforms are allowed
3. Create compliance policies: Devices → Compliance → + Create policy (per platform: Windows, iOS, Android)
4. Define compliance requirements: OS version, encryption, password complexity, threat level
5. Create device configuration profiles: Devices → Configuration → + Create profile
6. Configure app protection policies: Apps → App protection policies → + Create policy
7. Link compliance to Conditional Access: Create CA policy requiring 'Require device to be marked as compliant'
8. Deploy to pilot group first: Assign policies to a test group (10-20 devices) for 7 days
9. Monitor compliance status: Devices → Monitor → Device compliance → Filter by non-compliant
10. Address non-compliant devices: Contact device owners, provide remediation guidance
11. Expand enrollment to all managed devices after successful pilot
12. Set up regular compliance reporting: Weekly review of non-compliant device count

### Reference Documentation

- [Mobile App Protection Policies](https://learn.microsoft.com/mem/intune/apps/app-protection-policy)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Device enrollment configured for all supported platforms
- [ ] Compliance policies created and assigned to device groups
- [ ] Conditional Access linked to device compliance requirement
- [ ] Non-compliant devices identified and remediation tracked
- [ ] Pilot validated; policies expanded to full scope
- [ ] Regular compliance reporting cadence established

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 11. Microsoft Forms (Plan E5)

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Smaller user base of 0 active M365 users. Forms E5 can establish structured feedback culture essential for agent improvement and adoption insights.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Create intelligent Forms for continuous Copilot feedback collection. Use branching logic to gather detailed insights from different user personas (beginners vs. power users).

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Advanced Forms for Agent Workflows](https://learn.microsoft.com/microsoft-forms/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 12. Viva Insights - MyAnalytics (Full)

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | Insight |

### Current Situation

> Smaller user base of 0 active M365 users. MyAnalytics can establish data-driven productivity culture where Copilot usage is measurably linked to wellbeing improvements.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Enable MyAnalytics for leaders and power users first. Use personal productivity insights to demonstrate Copilot ROI through metrics like reduced after-hours work and increased focus time.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Personal Productivity Insights](https://learn.microsoft.com/viva/insights/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 13. Exchange Online (Plan 2) - Activity Baseline

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟡 Medium |
| **Status** | PendingActivation |

### Current Situation

> Email activity data unavailable: Unable to check email activity: 'ReportsRequestBuilder' object has no attribute 'get_email_activity_counts'

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Enable Reports.Read.All permission to access email activity reports. Baseline metrics are critical for measuring Copilot ROI.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Permission Blocked |
| **False Positive Risk** | High |
| **False Negative Risk** | Medium |
| **Confidence Level** | Low |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Configure Reports Permission](https://learn.microsoft.com/graph/permissions-reference#reportsreadall)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 14. Microsoft Entra ID P2

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | Action Required |

### Current Situation

> No active access reviews configured for user access governance

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Implement periodic access reviews for users with Copilot licenses and admin roles. Regular reviews ensure only authorized users maintain access to AI assistants and prevent license waste.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Configure Access Reviews](https://learn.microsoft.com/entra/id-governance/access-reviews-overview)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 15. Microsoft Entra ID P2

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | Action Required |

### Current Situation

> Cross-tenant access settings enabled but no partner organizations configured - default settings apply to all external tenants

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Define specific partner organization policies to control which external tenants can collaborate and access Copilot content. With default settings only: 1) All external organizations have the same access level, 2) Cannot enforce different MFA requirements per partner, 3) Cannot block specific high-risk tenants, 4) No granular control over app access per partner. Add trusted partner organizations with specific inbound/outbound policies, require MFA for external users, and block risky tenants. Review Microsoft's recommended baseline policy.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Configure Partner Organizations](https://learn.microsoft.com/entra/external-id/cross-tenant-access-settings-b2b-collaboration)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 16. Microsoft Entra ID P2

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | Action Required |

### Current Situation

> Application consent settings could not be verified - review tenant configuration to ensure proper app governance for Copilot data access

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Review application consent policies in Entra ID to ensure user consent is appropriately restricted. Verify that: 1) Users cannot consent to apps accessing organizational data without admin review, 2) Admin consent workflow is enabled for user requests, 3) Only verified publishers and low-risk permissions are allowed for user consent (if enabled). This prevents unauthorized apps from accessing emails, files, and other content searchable by Copilot.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Configure User Consent](https://learn.microsoft.com/entra/identity/enterprise-apps/configure-user-consent)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 17. Microsoft Entra ID P2

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | Action Required |

### Current Situation

> No access reviews configured - Copilot license assignments and privileged access not recertified

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Implement quarterly access reviews for Copilot governance. Without reviews: 1) Former employees retain Copilot access after role changes, 2) Licenses remain assigned to inactive users (wasted cost), 3) Guest users maintain access to Copilot-searchable content indefinitely, 4) No compliance audit trail for who approved continued access. Configure reviews for: 1) Groups with Copilot licenses (quarterly recertification of members), 2) Guest user access to Teams/SharePoint (remove stale external accounts), 3) Privileged roles (Copilot admins, Teams admins - monthly reviews). Use automated approval for active users, require justification for continued access to high-value resources. Essential for SOC 2, ISO 27001, and cost optimization.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Configure Access Reviews](https://learn.microsoft.com/entra/id-governance/deploy-access-reviews)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 18. Microsoft Entra ID P1

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | Action Required |

### Current Situation

> 5 Conditional Access policy(ies) configured, but none specifically target Copilot applications

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Create Copilot-specific Conditional Access policies targeting Microsoft 365 Copilot and Graph Connector applications. Apply stricter controls for AI access: require compliant devices, trusted locations, and MFA. Consider blocking Copilot access from unmanaged devices to prevent data exfiltration.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Conditional Access for Copilot](https://learn.microsoft.com/entra/identity/conditional-access/concept-conditional-access-cloud-apps)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 19. Microsoft Entra ID P1

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | Action Required |

### Current Situation

> Only 0.0% of users (0) use passwordless authentication, leaving Copilot vulnerable to password attacks

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Deploy passwordless authentication (FIDO2 security keys, Windows Hello for Business, or Microsoft Authenticator app) to eliminate password-based attacks targeting Copilot access. Passwordless methods are phishing-resistant and significantly reduce credential theft risks. Use Conditional Access to require passwordless auth for high-value resources like Copilot. Start with pilot groups and expand based on user feedback.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Deploy Passwordless Authentication](https://learn.microsoft.com/entra/identity/authentication/concept-authentication-passwordless)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 20. Microsoft Entra ID P1

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | Action Required |

### Current Situation

> No group-based licensing configured - Copilot licenses likely assigned manually to individual users

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Implement group-based licensing to automate Copilot license assignment and improve governance. Manual license assignment: 1) Creates administrative overhead for every new Copilot user, 2) Increases risk of orphaned licenses when users leave, 3) Lacks audit trail for compliance, 4) Cannot leverage dynamic groups for role-based access. Create security groups for Copilot users (e.g., 'Copilot-Sales', 'Copilot-Finance') and assign M365 licenses to groups. Use dynamic groups with rules like 'department equals Sales' to automatically assign/remove licenses based on user attributes. Configure license inheritance to cascade Copilot access to nested groups. This enables self-service access (users get Copilot when added to group), improves license reclamation, and provides clear governance model.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Configuration Gap |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Group-Based Licensing](https://learn.microsoft.com/entra/identity/users/licensing-groups-assign)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 21. Microsoft Entra Internet Access

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | PendingActivation |

### Current Situation

> Microsoft Entra Internet Access is PendingActivation in Microsoft Entra Suite - upgrade required for comprehensive AI traffic security

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Upgrade to Microsoft Entra Suite or Security Service Edge to enable Internet Access for AI security. Without secure web gateway, you cannot: 1) Detect shadow AI usage - employees using ChatGPT, Claude, Gemini to process corporate data outside M365 Copilot governance, 2) Monitor Copilot data exfiltration - users copying AI summaries to personal cloud storage or unauthorized AI platforms, 3) Block unauthorized AI tools - prevent employees from uploading sensitive documents to consumer AI services, 4) Inspect AI traffic for malware - detect credential harvesting or phishing via malicious AI tool sites. Internet Access provides: traffic visibility showing which AI services users access, web content filtering to block/warn for unauthorized AI platforms, DLP inspection of traffic to/from AI services, conditional access integration to enforce device compliance for AI access. Essential for preventing data leakage through AI tools outside your security perimeter.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Permission Blocked |
| **False Positive Risk** | High |
| **False Negative Risk** | Medium |
| **Confidence Level** | Low |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Global Secure Access Overview](https://learn.microsoft.com/entra/global-secure-access/overview-what-is-global-secure-access)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 22. Microsoft Entra Private Access

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟡 Medium |
| **Status** | PendingActivation |

### Current Situation

> Microsoft Entra Private Access is PendingActivation in Microsoft Entra Suite, limiting secure access to internal data sources for Copilot

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Enable Microsoft Entra Private Access to provide zero-trust network access to on-premises and private cloud resources that Copilot and custom agents need to query. Private Access eliminates VPN requirements while enforcing per-app access controls and continuous verification. Deploy agents that securely access internal databases, legacy systems, and private APIs without exposing them to the internet. Essential for extending Copilot's knowledge to include proprietary systems while maintaining zero-trust security posture.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Permission Blocked |
| **False Positive Risk** | High |
| **False Negative Risk** | Medium |
| **Confidence Level** | Low |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Zero-Trust Network for AI](https://learn.microsoft.com/entra/global-secure-access/)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 23. Microsoft Places (Core)

| Field | Value |
|-------|-------|
| **Service** | `M365` |
| **Priority** | 🟢 Low |
| **Status** | Insight |

### Current Situation

> Smaller workforce of 0 active users. Microsoft Places can establish hybrid work coordination patterns essential for Copilot-powered space booking and team presence awareness as organization scales.

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

Implement Microsoft Places early to build hybrid work coordination culture. Even small teams benefit from knowing when colleagues plan office visits, enabling purposeful in-person collaboration rather than random office attendance.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Index Inferred |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Microsoft Places Overview](https://learn.microsoft.com/microsoft-365/places/overview)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 24. Microsoft Entra Internet Access

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟢 Low |
| **Status** | Access Denied |

### Current Situation

> Global Secure Access API returned HTTP 403 (Forbidden: Authentication failed with status code 403 (Forbidden).)

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

The Global Secure Access API returned HTTP 403. This typically means Global Secure Access is not activated or licensed in your tenant. If the service is activated, ensure the signed-in user has the Global Secure Access Administrator directory role (or Global Administrator). A Global Reader role alone is not sufficient for this API.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Unknown |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Global Secure Access Prerequisites](https://learn.microsoft.com/entra/global-secure-access/overview-what-is-global-secure-access)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

## 25. Microsoft Entra Private Access

| Field | Value |
|-------|-------|
| **Service** | `Entra` |
| **Priority** | 🟢 Low |
| **Status** | Access Denied |

### Current Situation

> Global Secure Access (Private Access) API returned HTTP 403 (Forbidden: Authentication failed with status code 403 (Forbidden).)

**Why this matters for Copilot:** This configuration contributes to the overall security and readiness posture required for Microsoft 365 Copilot deployment. Addressing this gap helps ensure Copilot operates within a properly secured environment.

### Recommended Action

The Global Secure Access API returned HTTP 403. This typically means Global Secure Access is not activated or licensed in your tenant. If the service is activated, ensure the signed-in user has the Global Secure Access Administrator directory role (or Global Administrator). A Global Reader role alone is not sufficient for this API.

### Risk Assessment

| Risk Factor | Assessment |
|-------------|-----------|
| **Telemetry Limitation** | Unknown |
| **False Positive Risk** | Medium |
| **False Negative Risk** | Medium |
| **Confidence Level** | Medium |
| **Impact if Not Addressed** | Medium — may affect Copilot readiness posture |

### Step-by-Step Implementation

1. Review the current configuration state in the relevant admin portal
2. Access the appropriate admin center: [Entra](https://entra.microsoft.com), [M365](https://admin.microsoft.com), [Security](https://security.microsoft.com), or [Compliance](https://compliance.microsoft.com)
3. Consult the official Microsoft documentation linked in the Reference section below
4. Plan implementation approach: Define scope, responsible parties, and target timeline
5. Configure changes in a test/pilot scope first (limited user group or report-only mode)
6. Validate changes produce expected results without adverse impact on users
7. Monitor for 7-14 days post-implementation for any issues or regressions
8. Document all changes made, including configuration details and rollback procedures
9. Schedule follow-up review to confirm sustained compliance in next assessment cycle

### Reference Documentation

- [Global Secure Access Prerequisites](https://learn.microsoft.com/entra/global-secure-access/overview-what-is-global-secure-access)
- [Microsoft Learn — M365 Security](https://learn.microsoft.com/en-us/microsoft-365/security/)

### Success Criteria

- [ ] Configuration completed as per recommendation
- [ ] Changes validated in the admin portal — correct settings confirmed
- [ ] No adverse impact on users or services observed during monitoring period
- [ ] Documentation updated with new configuration and rollback procedures
- [ ] Next assessment expected to show improved/resolved status

### Implementation Notes

```
Assigned to:             ___________________________
Target completion date:   ___________________________
Status:                   ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Blocked
Notes:                    
```

---

# Appendix

## Related Resources

| Portal | URL |
|--------|-----|
| Microsoft Entra admin center | https://entra.microsoft.com |
| Microsoft 365 admin center | https://admin.microsoft.com |
| Microsoft Defender portal | https://security.microsoft.com |
| Microsoft Purview compliance | https://compliance.microsoft.com |
| SharePoint admin center | https://admin.microsoft.com/sharepoint |
| Microsoft Intune | https://intune.microsoft.com |
| Azure portal | https://portal.azure.com |
| My Security Info (users) | https://aka.ms/mysecurityinfo |
| FastTrack | https://fasttrack.microsoft.com |

## Priority Matrix

| Priority | Target Timeline | Description |
|----------|----------------|-------------|
| 🔴 Critical | Immediate (1-7 days) | Active security gaps requiring urgent remediation |
| 🟠 High | 30 days | Significant risks that should be addressed promptly |
| 🟡 Medium | 90 days | Important improvements for overall readiness posture |
| 🟢 Low | 120 days | Optimizations and enhancements for long-term posture |

## Acronyms Glossary

| Acronym | Full Term |
|---------|-----------|
| CA | Conditional Access |
| MFA | Multi-Factor Authentication |
| MDE | Microsoft Defender for Endpoint |
| XDR | Extended Detection and Response |
| DLP | Data Loss Prevention |
| RBAC | Role-Based Access Control |
| FIDO2 | Fast Identity Online 2 |
| AIR | Automated Investigation and Response |
| SPO | SharePoint Online |
| OAuth | Open Authorization |
| EDR | Endpoint Detection and Response |
| ASR | Attack Surface Reduction |
| B2B | Business-to-Business |
| SCCM | System Center Configuration Manager |
| SOC | Security Operations Center |
| BYOD | Bring Your Own Device |

## Support Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Project Lead | | | |
| Security Architect | | | |
| Identity Admin | | | |
| M365 Admin | | | |
| Help Desk Lead | | | |
| Microsoft TAM/CSM | | | |

---

*Document generated on May 24, 2026 | Total action items: 25 | Methodology: M365 Copilot Assessment Insights Generator — Step 2*

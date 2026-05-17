# Change Activity: Fix Purview Device Code Authentication

**Start:** 2026-05-13 22:00
**End:** PENDING
**Goal:** Fix Purview `--auth-mode device_code` flow so it works end-to-end

## Root Cause

1. `ExchangeOnlineManagement` PowerShell module is **not installed** in `pwsh` → `collect_purview_data.ps1` exits immediately at module check
2. Even after installing it, `Connect-IPPSSession -Device` writes device code URL to PowerShell **host stream** (stream 6), which is neither stdout nor stderr → Python subprocess cannot display it to the user
3. `stream_stderr()` in `orchestrator_powershell.py` only handles lines starting with `AUTH_COMPLETE:` → all other stderr lines (errors, warnings) are silently dropped

## Changes

---

### PREREQUISITE: Install ExchangeOnlineManagement module

```powershell
# Run once:
Install-Module ExchangeOnlineManagement -Scope CurrentUser -Force
```

---

### CHANGE 1: collect_purview_data.ps1 — Redirect host stream to stderr

**Purpose:** Make device code prompts visible to the Python parent process by redirecting PowerShell host stream (6) to stderr (2).

**File:** `collect_purview_data.ps1`
**Lines:** ~67-70 and ~87-90

**BEFORE (IPPS connection, line ~67-69):**
```powershell
        if ($env:USE_DEVICE_CODE -eq "1") {
            Connect-IPPSSession -Device -ErrorAction Stop -WarningAction SilentlyContinue | Out-Null
        } else {
```

**AFTER:**
```powershell
        if ($env:USE_DEVICE_CODE -eq "1") {
            Connect-IPPSSession -Device -ErrorAction Stop -WarningAction SilentlyContinue 6>&2 | Out-Null
        } else {
```

**BEFORE (Exchange connection, line ~88-90):**
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue | Out-Null
            } else {
```

**AFTER:**
```powershell
            if ($env:USE_DEVICE_CODE -eq "1") {
                Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue 6>&2 | Out-Null
            } else {
```

---

### CHANGE 2: orchestrator_powershell.py — Forward all stderr lines to user

**Purpose:** Show errors, device code URLs, and warnings to the user instead of silently dropping them. Only `AUTH_COMPLETE:` lines get special handling; everything else is displayed as-is.

**File:** `Core/orchestrator_powershell.py`
**Lines:** ~210-229

**BEFORE:**
```python
    # Stream stderr in real-time to show authentication progress
    def stream_stderr():
        try:
            for line in process.stderr:
                line = line.strip()
                if line.startswith('AUTH_COMPLETE:'):
                    service = line.split(':', 1)[1]
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ✅ {service} authentication accepted\n')
                        # After Security & Compliance, prompt for Exchange Online
                        if 'Security & Compliance' in service:
                            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Please provide credentials for Exchange Online authentication...\n')
                            sys.stdout.flush()
                            # Start spinner for Exchange Online auth
                            start_spinner('Waiting for Exchange Online authentication...')
                        else:
                            sys.stdout.flush()
        except ValueError:
            # Pipe closed, thread can exit
            pass
```

**AFTER:**
```python
    # Stream stderr in real-time to show authentication progress and errors
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
                        sys.stdout.write(f'[{get_timestamp()}]   ✅ {service} authentication accepted\n')
                        # After Security & Compliance, prompt for Exchange Online
                        if 'Security & Compliance' in service:
                            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Please provide credentials for Exchange Online authentication...\n')
                            sys.stdout.flush()
                            # Start spinner for Exchange Online auth
                            start_spinner('Waiting for Exchange Online authentication...')
                        else:
                            sys.stdout.flush()
                else:
                    # Forward all other stderr lines (device code URLs, errors, warnings)
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   {line}\n')
                        sys.stdout.flush()
        except ValueError:
            # Pipe closed, thread can exit
            pass
```

---

## Rollback Instructions

1. **Revert collect_purview_data.ps1:** Remove ` 6>&2` from lines with `Connect-IPPSSession` and `Connect-ExchangeOnline` (device code branches only)
2. **Revert orchestrator_powershell.py:** Remove the `else:` block and the `if not line: continue` line from `stream_stderr()`
3. **Module:** `ExchangeOnlineManagement` can remain installed — it does not affect other functionality

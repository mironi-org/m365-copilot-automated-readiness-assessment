# CHANGE LOG — PowerShell Device Code Visibility Fix
# Started: 2026-05-14
# Goal: Make PowerShell device code from Connect-ExchangeOnline -Device visible to user
# Root Cause: MSAL writes device code via .NET Console.WriteLine (stdout), not PowerShell streams.
#   The *>&1 | ForEach-Object { [Console]::Error.WriteLine("$_") } pattern only captures
#   PowerShell streams (1-6), not .NET Console writes. Meanwhile Python read stdout with
#   blocking .read() — so the device code sat in the pipe buffer, never displayed.

---

## FILE 1: collect_purview_data.ps1

### CHANGE 1A: Remove *>&1 redirect from Connect-ExchangeOnline -Device

**BEFORE (line ~76):**
```powershell
$null = Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue *>&1 | ForEach-Object { [Console]::Error.WriteLine("$_") }
```

**AFTER:**
```powershell
Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue
```

### CHANGE 1B: Remove *>&1 redirect from Connect-IPPSSession -Device

**BEFORE (line ~92):**
```powershell
$null = Connect-IPPSSession -Device -ErrorAction Stop -WarningAction SilentlyContinue *>&1 | ForEach-Object { [Console]::Error.WriteLine("$_") }
```

**AFTER:**
```powershell
Connect-IPPSSession -Device -ErrorAction Stop -WarningAction SilentlyContinue
```

---

## FILE 2: Core/orchestrator_powershell.py

### CHANGE 2A: Replace blocking stdout.read() with threaded real-time reader

**BEFORE (lines ~207-250):**
- stderr streamed in thread (shows AUTH_COMPLETE signals)
- stdout read with blocking `process.stdout.read()` — device code stuck in pipe

**AFTER:**
- Added `stream_stdout()` thread that reads stdout line-by-line
- Device code lines (containing 'devicelogin' or 'enter the code') displayed in real-time
- All stdout lines buffered in `stdout_lines` list
- After process completes, stdout reconstructed from buffer for JSON extraction
- stderr thread unchanged (still handles AUTH_COMPLETE signals)

Key code:
```python
stdout_lines = []

def stream_stdout():
    try:
        for line in process.stdout:
            stripped = line.rstrip()
            stdout_lines.append(stripped)
            lower = stripped.lower()
            if stripped and ('devicelogin' in lower or 'enter the code' in lower or 'microsoft.com/device' in lower):
                stop_spinner()
                with _stdout_lock:
                    sys.stdout.write(f'\n{stripped}\n\n')
                    sys.stdout.flush()
    except ValueError:
        pass

stdout_thread = threading.Thread(target=stream_stdout, daemon=True)
stdout_thread.start()
# ... stderr_thread unchanged ...
process.wait()
stdout_thread.join(timeout=2.0)
stderr_thread.join(timeout=2.0)
stdout = '\n'.join(stdout_lines)
```

---

## ROLLBACK INSTRUCTIONS

### To revert collect_purview_data.ps1:
Replace the device code Connect-ExchangeOnline line with:
```powershell
$null = Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop -WarningAction SilentlyContinue *>&1 | ForEach-Object { [Console]::Error.WriteLine("$_") }
```
Replace the device code Connect-IPPSSession line with:
```powershell
$null = Connect-IPPSSession -Device -ErrorAction Stop -WarningAction SilentlyContinue *>&1 | ForEach-Object { [Console]::Error.WriteLine("$_") }
```

### To revert orchestrator_powershell.py:
Remove the `stdout_lines`, `stream_stdout()`, and `stdout_thread` additions.
Replace `process.wait()` + join logic with:
```python
stdout = process.stdout.read()
process.wait()
```

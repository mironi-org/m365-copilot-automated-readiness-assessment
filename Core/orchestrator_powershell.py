"""PowerShell subprocess management for orchestrator."""

import os
import sys
import subprocess
import threading
import time
from .spinner import get_timestamp, _stdout_lock


async def collect_power_platform_data(tenant_id, run_power_platform, run_copilot_studio):
    """Launch unified Power Platform/Copilot Studio data collector.
    
    This ensures single authentication and data sharing between both services.
    Sets environment variables that will be consumed by service pipelines.
    
    Args:
        tenant_id: Azure tenant ID
        run_power_platform: Whether Power Platform service is requested
        run_copilot_studio: Whether Copilot Studio service is requested
    """
    # Check if data already collected (avoid re-launch)
    if os.environ.get("POWER_PLATFORM_DATA_SOURCE"):
        return
    
    # Launch unified collector (PS1 files are in parent directory, not in Core)
    ps_script_path = os.path.join(os.path.dirname(__file__), "..", "collect_power_platform_and_copilot_studio_data.ps1")
    
    process = subprocess.Popen(
        ["pwsh", "-ExecutionPolicy", "Bypass", "-File", ps_script_path, "-DataOnly", "-TenantId", tenant_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )
    
    # Spinner control
    spinner_stop_event = threading.Event()
    
    def run_spinner(message):
        """Display a rotating spinner with message"""
        spinner_chars = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
        idx = 0
        while not spinner_stop_event.is_set():
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   {spinner_chars[idx]} {message}')
                sys.stdout.flush()
            idx = (idx + 1) % len(spinner_chars)
            time.sleep(0.1)
    
    def stop_spinner():
        """Stop and clear spinner"""
        spinner_stop_event.set()
        if spinner_thread.is_alive():
            spinner_thread.join(timeout=0.5)
        with _stdout_lock:
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.flush()
    
    # Determine spinner message based on which services are running
    if run_power_platform and run_copilot_studio:
        spinner_message = 'Collecting Power Platform & Copilot Studio data...'
    elif run_power_platform:
        spinner_message = 'Collecting Power Platform data...'
    else:  # run_copilot_studio only
        spinner_message = 'Collecting Copilot Studio data...'
    
    # Start spinner
    spinner_thread = threading.Thread(target=run_spinner, args=(spinner_message,), daemon=True)
    spinner_thread.start()
    
    # Stream output for real-time device code display
    stderr_lines = []
    stdout_lines = []
    
    def stderr_thread_func(process):
        try:
            for line in iter(process.stderr.readline, ''):
                if not line:
                    break
                stderr_lines.append(line.strip())
        except Exception:
            pass
    
    def stdout_thread_func(process):
        try:
            full_output = []
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                full_output.append(line)
                line_stripped = line.rstrip()
                # Display non-JSON output in real-time
                if line_stripped and not line_stripped.startswith('{'):
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'{line_stripped}\n')
                        sys.stdout.flush()
            stdout_lines.extend([l.rstrip() for l in full_output])
        except Exception:
            pass
    
    stderr_thread = threading.Thread(target=stderr_thread_func, args=(process,))
    stderr_thread.daemon = True
    stderr_thread.start()
    
    stdout_thread = threading.Thread(target=stdout_thread_func, args=(process,))
    stdout_thread.daemon = True
    stdout_thread.start()
    
    # Wait for completion
    process.wait()
    stop_spinner()
    stderr_thread.join(timeout=1.0)
    stdout_thread.join(timeout=1.0)
    
    # Extract JSON from stdout
    json_output = ''
    for line in reversed(stdout_lines):
        if line.startswith('{'):
            json_output = line
            break
    
    if json_output and process.returncode == 0:
        # Set environment variables for both services to consume
        os.environ["POWER_PLATFORM_DATA_SOURCE"] = "subprocess"
        os.environ["POWER_PLATFORM_DATA_JSON"] = json_output
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ✓ Data collection complete\n')
            sys.stdout.flush()
    elif process.returncode != 0:
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ✗ Data collection failed (will use basic recommendations)\n')
            sys.stdout.flush()


async def collect_purview_data_via_powershell():
    """Launch PowerShell to collect Purview data with interactive authentication.
    
    Graph token is pre-acquired via MSAL (single device code) to feed
    _StaticTokenCredential in get_graph_client(). EXO/IPPS authentication
    is handled by PowerShell modules using native -Device flow.
    
    Sets environment variables that will be consumed by get_purview_client.
    
    Returns:
        bool: True if data collection succeeded, False otherwise
    """
    use_device_code = os.environ.get('USE_DEVICE_CODE') == '1'
    
    # Pre-acquire Graph token via MSAL (populates _purview_tokens for _StaticTokenCredential)
    if use_device_code:
        try:
            from .get_graph_client import acquire_purview_tokens
            tenant_id = os.environ.get('TENANT_ID')
            client_id = os.environ.get('CLIENT_ID_STREAM3')
            acquire_purview_tokens(tenant_id, client_id)
        except Exception as e:
            with _stdout_lock:
                sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Graph token pre-acquisition failed: {e}\n')
                sys.stdout.flush()
    
    with _stdout_lock:
        sys.stdout.write(f'[{get_timestamp()}]   ℹ️  Launching PowerShell to collect Purview data...\n')
        if use_device_code:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Device code prompt will appear for Exchange Online authentication\n')
        else:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Browser authentication windows will appear\n')
        sys.stdout.flush()
    
    # Launch PowerShell — no token args, PS handles EXO/IPPS auth natively
    ps_script = os.path.join(os.path.dirname(__file__), '..', 'collect_purview_data.ps1')
    cmd = ['pwsh', '-ExecutionPolicy', 'Bypass', '-File', ps_script, '-DataOnly']
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1  # Line buffered
    )
    
    # Status message control (no animation — \r is unreliable on Windows terminals)
    def print_status(message):
        """Print a single status line (no spinner animation)"""
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ⏳ {message}\n')
            sys.stdout.flush()
    
    # Compatibility shims — other code calls start/stop_spinner
    def start_spinner(message):
        print_status(message)
    
    def stop_spinner():
        pass  # Nothing to stop — no background thread
    
    # Initial status
    print_status('Waiting for Exchange Online authentication...')
    
    # Shared buffer for stdout lines (threaded reader fills it, main thread extracts JSON later)
    stdout_lines = []
    
    # Stream stdout — display device code prompts from PS
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
    
    # Stream stderr in real-time to show authentication progress
    exo_connected = threading.Event()  # Set after EXO auth completes
    
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
                        sys.stdout.write(f'[{get_timestamp()}]   \u2705 {service} connected\n')
                        if 'Exchange Online' in service:
                            exo_connected.set()
                            sys.stdout.write(f'[{get_timestamp()}]   ⏳ Connecting to Security & Compliance...\n')
                            sys.stdout.flush()
                        else:
                            sys.stdout.flush()
                            start_spinner('Collecting Purview compliance data...')
                elif line.startswith('AUTH_SKIPPED:'):
                    service = line.split(':', 1)[1]
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ⚠️  {service} skipped (auth not available in device_code mode)\n')
                        sys.stdout.flush()
                        start_spinner('Collecting Purview compliance data (limited)...')
                elif line.startswith('ERROR:'):
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   ❌ {line}\n')
                        sys.stdout.flush()
                elif 'devicelogin' in line.lower() or 'enter the code' in line.lower() or 'microsoft.com/device' in line.lower():
                    # Device code URL may arrive via warning stream (stderr)
                    stop_spinner()
                    with _stdout_lock:
                        sys.stdout.write(f'\n{line}\n\n')
                        sys.stdout.flush()
                elif exo_connected.is_set():
                    # After EXO connected, show IPPS/other stderr (safe — no spinner race)
                    with _stdout_lock:
                        sys.stdout.write(f'[{get_timestamp()}]   {line}\n')
                        sys.stdout.flush()
                # Before EXO connects: ignore stderr (EXO module verbose noise)
        except ValueError:
            # Pipe closed, thread can exit
            pass
    
    stdout_thread = threading.Thread(target=stream_stdout, daemon=True)
    stdout_thread.start()
    stderr_thread = threading.Thread(target=stream_stderr, daemon=True)
    stderr_thread.start()
    
    # Wait for process to complete (with timeout to prevent indefinite hang)
    try:
        process.wait(timeout=300)  # 5 minute timeout
    except subprocess.TimeoutExpired:
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ⚠️  PowerShell process timed out after 5 minutes — terminating\n')
            sys.stdout.flush()
        process.kill()
        process.wait()
    result_returncode = process.returncode
    
    # Stop any remaining spinner
    stop_spinner()
    
    # Give threads time to finish processing remaining lines
    stdout_thread.join(timeout=2.0)
    stderr_thread.join(timeout=2.0)
    
    # Reconstruct stdout from buffered lines
    stdout = '\n'.join(stdout_lines)
    
    if result_returncode != 0:
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ✗ PowerShell data collection failed (exit code: {result_returncode})\n')
            sys.stdout.write(f'[{get_timestamp()}]   stdout captured: {len(stdout)} chars\n')
            sys.stdout.flush()
        return False
    
    # Parse JSON output from PowerShell
    import json
    try:
        # Extract just the JSON from the output (ignore warnings/banners)
        stdout_text = stdout.strip()
        # Find the JSON object (starts with { and ends with })
        json_start = stdout_text.find('{')
        json_end = stdout_text.rfind('}')
        if json_start >= 0 and json_end >= 0:
            json_str = stdout_text[json_start:json_end + 1]
            purview_data = json.loads(json_str)
            # Inject data for get_purview_client to consume
            os.environ['PURVIEW_DATA_SOURCE'] = 'subprocess'
            os.environ['PURVIEW_DATA_JSON'] = json_str
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Purview Data Gathering  [████████████████████] 100%\n')
                sys.stdout.flush()
            return True
        else:
            raise ValueError("No JSON found in PowerShell output")
    except (json.JSONDecodeError, ValueError) as e:
        with _stdout_lock:
            sys.stdout.write(f'[{get_timestamp()}]   ✗ Failed to parse PowerShell output: {e}\n')
            sys.stdout.flush()
        return False

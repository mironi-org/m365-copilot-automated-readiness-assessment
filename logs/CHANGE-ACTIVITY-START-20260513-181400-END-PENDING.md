# Change Activity Log (Start: 2026-05-13 18:14:00, End: PENDING)

## Changed - 2026-05-13 18:20:05
- File changed: Core/credentials_check.py
- What changed:
  - `load_env_file()`: Changed `os.environ[key] = value` to `os.environ.setdefault(key, value)`
  - This ensures that values already set by CLI argument parsing (e.g. `AUTH_MODE=device_code` from `--auth-mode device_code`) are NOT overwritten when the `.env` file is loaded afterward.
- Root cause fixed:
  - `validate_credentials_or_exit()` was called after `parse_arguments()` in main.py.
  - `parse_arguments()` correctly sets `os.environ['AUTH_MODE'] = 'device_code'`.
  - But `validate_credentials_or_exit()` calls `load_env_file()`, which read `AUTH_MODE=interactive` from `.env` and silently overwrote the CLI value.
  - Result: `get_graph_client()` always saw `AUTH_MODE=interactive` and opened a browser instead of printing the device code.
- Status: Completed at 2026-05-13 18:20:05.
- Conflict Check:
  - ✅ Does NOT affect service_principal mode
  - ✅ Does NOT affect interactive mode when AUTH_MODE is not overridden by CLI
  - ✅ CLI `--auth-mode` flag now correctly takes full precedence over `.env`
  - ✅ `.env` AUTH_MODE still applies when no CLI flag is given

## Changed - 2026-05-13 18:20:06
- File changed: Core/get_graph_client.py
- What changed (1): `_load_env()`: Same fix as credentials_check.py — changed `os.environ[key.strip()] = value` to `os.environ.setdefault(key.strip(), value)` so module-level env loading does not clobber CLI-set values.
- What changed (2): `_device_code_prompt_callback()`: Rewrote signature and body.
  - Old: `def _device_code_prompt_callback(*args)` — read `verification_uri = args[0]`, `user_code = args[1]`
  - New: `def _device_code_prompt_callback(device_code_info)` — reads `device_code_info.verification_uri` and `device_code_info.user_code`
  - Reason: Azure SDK passes a single `DeviceCodeInfo` object, not positional string arguments. Old code would always fall back to defaults and print `"(code unavailable)"` / `"https://microsoft.com/devicelogin"` instead of actual values.
  - Output improved: Now prints a clearly formatted box with step-by-step instructions (URL on one line, code on the next) to make it easy for the user to copy both values.
- Status: Completed at 2026-05-13 18:20:10.
- Conflict Check:
  - ✅ Only applies to auth_mode == 'device_code'
  - ✅ Does NOT affect interactive or service_principal modes
  - ✅ Callback is only registered on DeviceCodeCredential — no other code paths affected
  - ✅ Maintains per-stream CLIENT_ID resolution and cache key (auth_mode, client_id)

## Reverted - 2026-05-13 18:45:00
- File reverted: setup-interactive-auth.ps1
- What changed:
  - Restored the file to repository HEAD.
  - Removed temporary setup-copy helper files created during troubleshooting.
- Reason:
  - User requested full rollback of unapproved setup script changes.
- Status: Completed.

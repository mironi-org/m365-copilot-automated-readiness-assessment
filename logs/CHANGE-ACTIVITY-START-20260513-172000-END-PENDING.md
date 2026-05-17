# Change Activity Log (Start: 2026-05-13 17:20:00, End: 2026-05-13 18:14:00)

## Changed - 2026-05-13 17:21:00
- File to change: Core/cli_parser.py
- Exact code to change:
  - Updated CLI help and examples to clarify device code is only for the assessment step, not for setup.
  - Added explicit warning in CLI epilog and help text.
- Status: Completed at 2026-05-13 17:21:10.

## Changed - 2026-05-13 17:21:11
- File to change: Core/credentials_check.py
- Exact code to change:
  - Updated credential guidance to clarify device code is only for assessment, not setup.
  - Added explicit warning in help text.
- Status: Completed at 2026-05-13 17:21:15.

## Changed - 2026-05-13 17:22:00
- File to change: RUN.md
- Exact code to change:
  - Added "Run Examples: Interactive Browser Authentication by Stream" section with examples for Streams 1-5.
  - Added "Run Examples: Device Code Authentication by Stream" section with examples for Streams 1-5.
  - Shows how to run assessment with --auth-mode interactive and --auth-mode device_code for each stream.
- Status: Completed at 2026-05-13 17:22:10.

## Changed - 2026-05-13 17:23:00
- File to change: Core/get_graph_client.py
- Exact code to change:
  - Fixed device code authentication in get_graph_client() to show device code prompt immediately.
  - Fixed device code authentication in get_shared_credential() to show device code prompt immediately.
  - Added immediate token acquisition (get_token call) after creating DeviceCodeCredential in both functions.
  - This triggers the prompt_callback right away, showing device code URL + user code to terminal immediately.
  - Consistent behavior across Graph APIs and non-Graph APIs (Defender, Power Platform).
  - User no longer waits for first API call to see device code.
- Status: Completed at 2026-05-13 17:23:25.
- Conflict Check:
  - ✅ Only applies to auth_mode == 'device_code' (no fallback logic)
  - ✅ Does NOT affect interactive or service_principal modes
  - ✅ Maintains per-stream CLIENT_ID resolution via STREAM_CLIENT_ID_MAP
  - ✅ Maintains cache key (auth_mode, client_id) to avoid cross-mode collisions
  - ✅ Does NOT introduce any fallback between auth modes
  - ✅ setup-interactive-auth.ps1 (PowerShell) is not affected
  - ✅ Device code remains assessment-only feature

## Analysis - 2026-05-13 17:20:00
- Searched for device code authentication logic in setup-interactive-auth.ps1, Core/cli_parser.py, and Core/credentials_check.py.
- No device code logic found in setup-interactive-auth.ps1 (OK).
- Device code is present as an option in Core/cli_parser.py and Core/credentials_check.py.
- These files control CLI options and credential validation for the main assessment tool.
- To enforce requirements:
  - Device code should only be available for the assessment step, not for setup-interactive-auth.ps1.
  - CLI and help text should clarify device code is not available for setup.
  - No changes needed in setup-interactive-auth.ps1.
- Next: Update CLI help and credential guidance to clarify device code is only for assessment, not setup.

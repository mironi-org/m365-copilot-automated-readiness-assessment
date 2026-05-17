# Change Activity Log (Start: 2026-05-13 17:05:39, End: 2026-05-13 17:10:17)

## Changed - 2026-05-13 17:05:39
- File touched: CHANGE-ACTIVITY-START-20260513-170539-END-PENDING.md
- Exact code to change:
  - Create this running activity log file.
  - Add per-file timestamped entries during implementation.
- Status: Completed.

## Changed - 2026-05-13 17:06:10
- File to change: Core/cli_parser.py
- Exact code to change:
  - Extend --auth-mode choices to include device_code.
  - Update help text and examples to document device-code authentication flow.
- Status: Completed at 2026-05-13 17:06:55.
- Exact code changed:
  - Added `device_code` to `--auth-mode` choices.
  - Added `device_code` command examples in parser epilog.
  - Updated help text to include verification URL + code flow.

## Changed - 2026-05-13 17:06:10
- File to change: Core/credentials_check.py
- Exact code to change:
  - Treat device_code like interactive for required variables (TENANT_ID required, CLIENT_SECRET not required).
  - Update credential guidance text to include device code mode.
- Status: Completed at 2026-05-13 17:07:32.
- Exact code changed:
  - Updated auth-mode check to treat `device_code` as delegated auth (no client secret requirement).
  - Added startup guidance lines for `AUTH_MODE=device_code` and `--auth-mode device_code`.

## Changed - 2026-05-13 17:06:10
- File to change: Core/get_graph_client.py
- Exact code to change:
  - Add DeviceCodeCredential import.
  - Add a device-code prompt callback to print verification URI and user code.
  - Add auth-mode branch for device_code in both Graph and shared credential factories.
  - Adjust credential cache keys to include auth mode + client_id.
- Status: Completed at 2026-05-13 17:10:12.
- Exact code changed:
  - Imported `DeviceCodeCredential`.
  - Added `_device_code_prompt_callback()` to print URL + code + waiting message in terminal.
  - Updated delegated auth branches to support both `interactive` and `device_code`.
  - Updated cache keys from `client_id` to `(auth_mode, client_id)` to avoid cross-mode collisions.
  - Kept service principal flow unchanged.

## Changed - 2026-05-13 17:06:10
- File to change: RUN.md
- Exact code to change:
  - Add run examples for --auth-mode device_code.
  - Update text explaining that device code mode shows URL+code and continues after successful auth.
- Status: Completed at 2026-05-13 17:11:15.
- Exact code changed:
  - Added CLI examples using `--auth-mode device_code`.
  - Added delegated-auth explanation for interactive vs device_code under execution flow.
  - Added sample terminal output showing URL + one-time code + waiting message.

## Changed - 2026-05-13 17:07:54
- File touched: CHANGE-ACTIVITY-START-20260513-170539-END-PENDING.md
- Exact code changed:
  - Finalized end timestamp in log header.
  - Added session close entry before renaming file.
- Status: Completed.

## Changed - 2026-05-13 17:10:35
- File to change: Core/cli_parser.py
- Exact code to change:
  - Add explicit Purview example using `--auth-mode device_code --services Purview`.
- Status: Completed at 2026-05-13 17:11:08.
- Exact code changed:
  - Added Purview command example in CLI epilog for `device_code` mode.

## Changed - 2026-05-13 17:10:35
- File to change: RUN.md
- Exact code to change:
  - Add explicit Purview example using `--auth-mode device_code`.
  - Clarify that Purview deployment-data collection uses PowerShell interactive auth prompts in `collect_purview_data.ps1`.
- Status: Completed at 2026-05-13 17:11:42.
- Exact code changed:
  - Added Purview `device_code` command example.
  - Clarified Purview authentication path via PowerShell prompts for Security & Compliance + Exchange Online.

## Changed - 2026-05-13 17:10:17
- File touched: CHANGE-ACTIVITY-START-20260513-170539-END-PENDING.md
- Exact code changed:
  - Finalized updated end timestamp after Purview follow-up updates.
  - Prepared file for final rename with end timestamp in filename.
- Status: Completed.

# Implementation Plan: Interactive Auth (Browser Login)

## Objective

Enable interactive browser authentication using the well-known Microsoft Graph PowerShell client ID. No custom app registration needed — users only need `TENANT_ID`.

---

## `.env`

```ini
TENANT_ID=<tenant-id>
AUTH_MODE=interactive
```

No `CLIENT_ID` or `CLIENT_SECRET` needed. Uses well-known Graph PowerShell client ID `14d82eec-204b-4c2f-b7e8-296a70dab67e`.

---

## Solution

`InteractiveBrowserCredential` opens the default browser for login. The credential is cached in the module so subsequent API calls (Graph, Defender, Power Platform) reuse the same token without re-prompting.

---

## Files Modified

| # | File | Change | Status |
|---|------|--------|--------|
| 1 | `Core/credentials_check.py` | Skip `CLIENT_ID`/`CLIENT_SECRET` check when `AUTH_MODE=interactive` | Done |
| 2 | `Core/get_graph_client.py` | Use well-known client ID, `InteractiveBrowserCredential` for interactive mode | Done |
| 3 | `Core/cli_parser.py` | `--auth-mode` choices: `service_principal`, `interactive` | Done |

---

## Code: `Core/get_graph_client.py`

```python
GRAPH_POWERSHELL_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"

if auth_mode == 'interactive':
    client_id = os.getenv('CLIENT_ID') or GRAPH_POWERSHELL_CLIENT_ID
    
    _credential = InteractiveBrowserCredential(
        tenant_id=tenant_id,
        client_id=client_id
    )
```

Both `get_graph_client()` and `get_shared_credential()` use the same cached `_credential`.

---

## One-Time Tenant Setup

If the tenant blocks the Graph PowerShell app, admin must consent once (InPrivate browser):

```
https://login.microsoftonline.com/{tenant-id}/adminconsent?client_id=14d82eec-204b-4c2f-b7e8-296a70dab67e&redirect_uri=http://localhost
```

The "localhost refused" page after consent is expected and harmless.

---

## Execution

```bash
python main.py --auth-mode interactive --services M365 Entra
```

Browser opens → user logs in → assessment runs.

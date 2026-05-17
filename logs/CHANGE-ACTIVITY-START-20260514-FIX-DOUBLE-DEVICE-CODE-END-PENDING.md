# CHANGE LOG — Fix Double Device-Code Prompt for Purview (silent=True)
# Started: 2026-05-14
# Status: PENDING VALIDATION
# Goal: Reduce Purview device-code authentication from 3 prompts to 2

---

## PROBLEM SUMMARY

When running `python main.py --auth-mode device_code --services Purview`,
user sees **3** device-code prompts:

1. Python `_device_code_prompt` — from explicit `credential.get_token()` in `get_graph_client()`
2. Python `_device_code_prompt` — from Graph SDK's internal `credential.get_token()` during `subscribed_skus.get()`
3. PowerShell `Connect-ExchangeOnline -Device`

**Root cause:** MSAL token cache (azure-identity 1.25.3 / msal 1.36.0) does not
serve the cached token from the explicit `get_token()` to the Graph SDK's internal
`get_token()` call made by kiota's `AzureIdentityAccessTokenProvider`. Both calls
use the identical scope `'https://graph.microsoft.com/.default'`, but MSAL treats
them as separate requests and triggers a second device code flow.

For **non-silent** services (M365, Entra, Defender), this doesn't happen because
`analyze_service_plans()` calls `get_graph_client()` first (triggering auth), and
then `setup_graph_and_licenses()` hits the `_graph_clients` cache and returns the
already-authenticated client. The explicit `get_token()` is only hit once.

For **Purview** (silent=True), `analyze_service_plans()` returns early (no graph
analysis needed), so `setup_graph_and_licenses()` is the FIRST call to
`get_graph_client()`. The explicit `get_token()` fires device code prompt #1, then
the SDK's `subscribed_skus.get()` fires prompt #2 (cache miss).

**Fix:** Gate the explicit `get_token()` on `not silent`. When `silent=True`,
the Graph SDK acquires the token lazily on the first API call — ONE prompt instead
of two.

---

## FILE: Core/get_graph_client.py

### CHANGE: Gate explicit get_token() on `not silent`

**BEFORE (lines ~146-163):**
```python
        # Force token acquisition NOW — triggers the device code prompt or browser
        # popup immediately, ensures "Authenticated" prints only after real auth,
        # and caches the token so subsequent API calls reuse it (no double prompts).
        # Wrapped in try/except because some stream apps (e.g. Stream 4 Power Platform)
        # may not have Graph permissions — Azure AD would refuse the token.
        # In that case we fall through: GraphServiceClient is still created (lazy auth)
        # and the downstream try/except in setup_graph_and_licenses handles the failure.
        token_acquired = False
        try:
            credential.get_token('https://graph.microsoft.com/.default')
            token_acquired = True
        except Exception:
            if not silent:
                print(f"[{get_timestamp()}] ⚠️  Graph token not available for this app (may lack Graph API permissions)")
                import sys
                sys.stdout.flush()
        
        if token_acquired and not silent:
            print(f"[{get_timestamp()}] ✅ Authenticated successfully")
            import sys
            sys.stdout.flush()
```

**AFTER:**
```python
        # Force token acquisition NOW for non-silent mode — triggers the device
        # code prompt or browser popup immediately, ensures "Authenticated" prints
        # only after real auth.
        # For silent mode (e.g. Purview-only): skip explicit get_token() and let
        # the Graph SDK acquire the token lazily on the first API call.  This
        # avoids a double device-code prompt caused by MSAL not serving the
        # cached token to the SDK's internal get_token() call (azure-identity
        # 1.25.x / msal 1.36.x).
        token_acquired = False
        if not silent:
            try:
                credential.get_token('https://graph.microsoft.com/.default')
                token_acquired = True
            except Exception:
                print(f"[{get_timestamp()}] ⚠️  Graph token not available for this app (may lack Graph API permissions)")
                import sys
                sys.stdout.flush()
            
            if token_acquired:
                print(f"[{get_timestamp()}] ✅ Authenticated successfully")
                import sys
                sys.stdout.flush()
```

**What changed:**
- Wrapped the `credential.get_token()` call and its success/error messages inside `if not silent:`
- When `silent=True` (Purview, Power Platform), the explicit token acquisition is SKIPPED
- The Graph SDK's lazy auth triggers ONE device code prompt during `subscribed_skus.get()`
- Non-silent services (M365, Entra, Defender) are UNAFFECTED — they still get immediate auth with messages

---

## EXPECTED RESULT AFTER FIX

`python main.py --auth-mode device_code --services Purview` should show:

1. **ONE** Python device code prompt (from SDK during `subscribed_skus.get()`)
2. **ONE** PowerShell device code prompt (from `Connect-ExchangeOnline -Device`)
3. **Possibly ONE** more PowerShell prompt (from `Connect-IPPSSession -Device` if not auto-connected)

Total: **2** prompts (down from 3), or 3 if IPPS requires separate auth.

---

## ROLLBACK

Restore the original `get_graph_client.py` from any `.env.bak.*` snapshot, or
reverse the change: remove the `if not silent:` guard and restore the unconditional
`credential.get_token()` call per the BEFORE block above.

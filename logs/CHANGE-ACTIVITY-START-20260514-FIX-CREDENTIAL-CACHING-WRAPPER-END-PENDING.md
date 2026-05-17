# FIX: Double Device Code Prompt — Credential Caching Wrapper (Phase 3)

## STATUS: IMPLEMENTED (2026-05-14)

## ISSUE

After Phase 2 (SKU cache), the double device-code prompt still occurs when running
`--services M365 Entra`. Root cause: `get_entra_client.py` line 33 calls
`credential.get_token('https://graph.microsoft.com/.default')` directly during the
Entra data gathering pipeline. Due to the MSAL cache bug (azure-identity 1.25.x /
msal 1.36.x), this triggers a **second device-code prompt** even though the same
scope was already authenticated during `analyze_service_plans()`.

Multiple other files also call `credential.get_token()` directly:
- `get_graph_client.py:441` — `prewarm_credentials()`
- `get_graph_client.py:478` — `get_api_client()`
- `get_defender_client.py:475`
- `get_power_platform_client.py:308,312`

**Fix:** Wrap `DeviceCodeCredential` / `InteractiveBrowserCredential` in a
`_CachingCredentialWrapper` class inside `_create_interactive_credential()`.
After the first successful `get_token()`, the wrapper returns the cached token
on subsequent calls with the same scope — no MSAL round-trip, no duplicate prompt.

---

## FILE 1: Core/get_graph_client.py

### CHANGE: Add `_CachingCredentialWrapper` class and use it in `_create_interactive_credential()`

**BEFORE (lines 82–99):**
```python
def _create_interactive_credential(tenant_id, client_id):
    """Create the appropriate interactive credential based on USE_DEVICE_CODE env var.
    
    In interactive mode with per-stream apps: each stream's app has its own credential,
    cached by client_id. Same stream won't prompt twice, different streams will each
    require one auth (assuming admin consent is pre-granted for all app permissions).
    """
    if os.getenv('USE_DEVICE_CODE') == '1':
        return DeviceCodeCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            prompt_callback=_device_code_prompt
        )
    return InteractiveBrowserCredential(
        tenant_id=tenant_id,
        client_id=client_id
    )
```

**AFTER:**
```python
class _CachingCredentialWrapper:
    """Wraps an azure-identity credential and caches tokens by scope.

    Works around an MSAL bug (azure-identity 1.25.x / msal 1.36.x) where
    DeviceCodeCredential.get_token() triggers a new device-code prompt even
    when a valid token is already cached internally.  After the first
    successful get_token() for a given scope, subsequent calls return the
    cached AccessToken without touching MSAL.
    """

    def __init__(self, inner):
        self._inner = inner
        self._cache = {}          # {scope_key: AccessToken}

    def get_token(self, *scopes, **kwargs):
        import time
        key = tuple(sorted(scopes))
        cached = self._cache.get(key)
        if cached and cached.expires_on > time.time() + 60:
            return cached
        token = self._inner.get_token(*scopes, **kwargs)
        self._cache[key] = token
        return token

    # Forward any other attribute access to the inner credential so the
    # Graph SDK (and other callers) can use it transparently.
    def __getattr__(self, name):
        return getattr(self._inner, name)


def _create_interactive_credential(tenant_id, client_id):
    """Create the appropriate interactive credential based on USE_DEVICE_CODE env var.
    
    In interactive mode with per-stream apps: each stream's app has its own credential,
    cached by client_id. Same stream won't prompt twice, different streams will each
    require one auth (assuming admin consent is pre-granted for all app permissions).
    """
    if os.getenv('USE_DEVICE_CODE') == '1':
        inner = DeviceCodeCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            prompt_callback=_device_code_prompt
        )
    else:
        inner = InteractiveBrowserCredential(
            tenant_id=tenant_id,
            client_id=client_id
        )
    return _CachingCredentialWrapper(inner)
```

---

## ROLLBACK INSTRUCTIONS

1. **Core/get_graph_client.py** — Remove the entire `_CachingCredentialWrapper` class
   (approx 25 lines) and revert `_create_interactive_credential()` to return the raw
   credential directly (no wrapper).

Exact rollback: replace the AFTER block above with the BEFORE block.

---

## RISK ASSESSMENT

- **Risk Level:** Low
- **Affected file:** 1 file (`Core/get_graph_client.py`)
- **Behavioral change:** All `credential.get_token()` calls for the same scope now
  return a cached `AccessToken` object instead of calling MSAL. The cache is per-scope
  and respects expiry (60-second buffer).
- **Side effects:** None — the wrapper is transparent to all callers via `__getattr__`.
  Service principal mode is unaffected (wrapper only applies to interactive credentials).
- **Relationship to Phase 2 (SKU cache):** Both fixes can coexist. The SKU cache avoids
  a redundant Graph API call; the credential wrapper prevents MSAL from re-prompting
  on any `get_token()` call. Together they eliminate all known double-prompt scenarios.

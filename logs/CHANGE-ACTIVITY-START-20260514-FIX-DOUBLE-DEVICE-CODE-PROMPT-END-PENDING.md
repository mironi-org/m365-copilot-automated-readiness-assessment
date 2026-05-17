# FIX: Double Device Code Prompt in Stream 1 & 2

## STATUS: IMPLEMENTED (2026-05-14)

## ISSUE

Streams 1 (M365/Entra) and 2 (Defender) trigger **two** device code prompts instead of one.

**Root cause:** `get_graph_client()` does an explicit `credential.get_token('https://graph.microsoft.com/.default')` 
to trigger the device code prompt immediately. Then the Graph SDK internally calls `get_token()` again on the first 
API call (`subscribed_skus.get()`), and MSAL (azure-identity 1.25.x / msal 1.36.x) does NOT serve the cached token — 
it initiates a new device code flow. The codebase already had a comment documenting this bug for Purview's `silent=True` 
workaround, but Streams 1 & 2 still used `silent=False` which hit the explicit `get_token()` path.

**Fix:** Remove the explicit `credential.get_token()` call entirely — let the Graph SDK acquire the token lazily 
on its first API call. Print the "Authenticating..." message immediately after credential creation (before SDK use), 
and print "Authenticated successfully" after the first successful SDK call in `setup_graph_and_licenses()`.

---

## FILE 1: Core/get_graph_client.py

### CHANGE 1: Remove explicit credential.get_token() — let SDK handle it lazily

**BEFORE (lines 227–252):**
```python
        credential = _credentials[client_id]
        
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
        
        # For interactive with per-stream apps: use .default (admin pre-granted consent)
        scopes = ['https://graph.microsoft.com/.default']
```

**AFTER:**
```python
        credential = _credentials[client_id]
        
        # Do NOT call credential.get_token() explicitly here.
        # Let the Graph SDK acquire the token lazily on its first API call.
        # Calling get_token() eagerly causes a DOUBLE device-code prompt because
        # MSAL (azure-identity 1.25.x / msal 1.36.x) does not reliably serve
        # the cached token when the SDK calls get_token() internally afterward.
        # The "Authenticated" message is printed by setup_graph_and_licenses()
        # after the first successful SDK call (subscribed_skus.get()).
        
        # For interactive with per-stream apps: use .default (admin pre-granted consent)
        scopes = ['https://graph.microsoft.com/.default']
```

---

## FILE 2: Core/orchestrator_setup.py

### CHANGE 2: Print "Authenticated" after first successful SDK call instead of in get_graph_client

**BEFORE (lines 58–78):**
```python
    # Always create Graph client (needed for license checks in all services)
    # Use silent mode for PowerShell-only runs (Purview, Power Platform)
    client = await get_graph_client(tenant_id, silent=not show_graph_messages, services=services)
    if show_graph_messages:
        print(f"[{get_timestamp()}] ✅ Connected to Microsoft Graph (Service Principal)")
    
    # Setup services container (needed by all pipelines)
    services_and_licenses = ServicesAndLicenses()
    has_license_data = False
    try:
        subscribed_skus = await client.subscribed_skus.get()
        if subscribed_skus:
            await services_and_licenses.set_raw_subscribed_skus(subscribed_skus)
            has_license_data = True
    except Exception as e:
        pass
    
    return client, services_and_licenses, has_license_data
```

**AFTER:**
```python
    # Always create Graph client (needed for license checks in all services)
    # Use silent mode for PowerShell-only runs (Purview, Power Platform)
    client = await get_graph_client(tenant_id, silent=not show_graph_messages, services=services)
    
    # Setup services container (needed by all pipelines)
    services_and_licenses = ServicesAndLicenses()
    has_license_data = False
    try:
        subscribed_skus = await client.subscribed_skus.get()
        if subscribed_skus:
            await services_and_licenses.set_raw_subscribed_skus(subscribed_skus)
            has_license_data = True
        if show_graph_messages:
            print(f"[{get_timestamp()}] ✅ Authenticated successfully")
    except Exception as e:
        if show_graph_messages:
            print(f"[{get_timestamp()}] ⚠️  Graph API call failed (may lack permissions): {e}")
    
    return client, services_and_licenses, has_license_data
```

---

## FILE 3: Core/check_all_service_plans.py

### CHANGE 3: Pass silent=True so analyze_service_plans does not trigger its own auth prompt

**BEFORE (line 34):**
```python
    # Get all service plans from tenant (shows auth messages)
    client = await get_graph_client(tenant_id, services=services_to_run)
```

**AFTER:**
```python
    # Get all service plans from tenant (silent=True — auth prompt deferred to setup_graph_and_licenses)
    client = await get_graph_client(tenant_id, silent=True, services=services_to_run)
```

---

## ROLLBACK INSTRUCTIONS

To revert all changes, restore the original code blocks shown in the BEFORE sections above:

1. **Core/get_graph_client.py** — restore the explicit `credential.get_token()` block with `token_acquired` logic
2. **Core/orchestrator_setup.py** — restore `"Connected to Microsoft Graph (Service Principal)"` message before `subscribed_skus.get()`, remove error handling in except
3. **Core/check_all_service_plans.py** — remove `silent=True` from `get_graph_client()` call

---

## RISK ASSESSMENT

- **Risk Level:** Low
- **Affected files:** 3 files
- **Affected streams:** Stream 1 (M365/Entra), Stream 2 (Defender) — both currently show 2 prompts, will show 1 after fix
- **Side effects:** None — Streams 3/4/5 already use silent mode or PowerShell auth, unaffected
- **Tested behavior:** The codebase comment at get_graph_client.py line 233 already documents that silent/lazy mode avoids the double-prompt bug

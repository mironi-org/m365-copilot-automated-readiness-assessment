# FIX: Double Device Code Prompt — SKU Cache (Phase 2)

## STATUS: IMPLEMENTED (2026-05-14)

## ISSUE

After removing the explicit `credential.get_token()` in Phase 1, the double device-code
prompt persisted. Root cause: **two separate `subscribed_skus.get()` calls** each trigger
the Graph SDK's internal lazy `get_token()`, and MSAL's cache bug causes a second prompt.

**Call order:**
1. `load_modules_and_analyze()` → `analyze_service_plans()` → `client.subscribed_skus.get()` → **prompt #1**
2. `setup_graph_and_licenses()` → `client.subscribed_skus.get()` → MSAL cache miss → **prompt #2**

**Fix:** Add a module-level SKU cache in `get_graph_client.py`. `analyze_service_plans()`
stores the SKU result after fetching. `setup_graph_and_licenses()` checks the cache first
and skips the redundant `subscribed_skus.get()` call entirely.

---

## FILE 1: Core/get_graph_client.py

### CHANGE: Add module-level SKU cache (`_cached_subscribed_skus`)

**BEFORE (lines 60–65):**
```python
_graph_clients = {} # {client_id: GraphServiceClient}

# Legacy single-credential cache (service principal mode)
_graph_client = None
_credential = None
```

**AFTER:**
```python
_graph_clients = {} # {client_id: GraphServiceClient}

# Cached subscribed SKUs — populated by analyze_service_plans(), consumed by
# setup_graph_and_licenses() to avoid a second subscribed_skus.get() call
# which would trigger a duplicate device-code prompt (MSAL cache bug).
_cached_subscribed_skus = None

# Legacy single-credential cache (service principal mode)
_graph_client = None
_credential = None
```

---

## FILE 2: Core/check_all_service_plans.py

### CHANGE: Store SKU result in cache after fetch

**BEFORE (lines 43–44):**
```python
    try:
        skus = await client.subscribed_skus.get()
```

**AFTER:**
```python
    from . import get_graph_client as _gc_module
    try:
        skus = await client.subscribed_skus.get()
        _gc_module._cached_subscribed_skus = skus  # Cache for setup_graph_and_licenses()
```

---

## FILE 3: Core/orchestrator_setup.py

### CHANGE: Use cached SKUs instead of calling subscribed_skus.get() again

**BEFORE (lines 59–76):**
```python
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

**AFTER:**
```python
    client = await get_graph_client(tenant_id, silent=not show_graph_messages, services=services)
    
    # Setup services container (needed by all pipelines)
    services_and_licenses = ServicesAndLicenses()
    has_license_data = False
    try:
        # Reuse SKUs cached by analyze_service_plans() to avoid a second
        # subscribed_skus.get() call which triggers a duplicate device-code
        # prompt (MSAL cache bug in azure-identity 1.25.x / msal 1.36.x).
        from . import get_graph_client as _gc_module
        subscribed_skus = _gc_module._cached_subscribed_skus
        if subscribed_skus is None:
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

## ROLLBACK INSTRUCTIONS

1. **Core/get_graph_client.py** — Remove `_cached_subscribed_skus = None` and its comment (3 lines)
2. **Core/check_all_service_plans.py** — Remove `from . import get_graph_client as _gc_module` and `_gc_module._cached_subscribed_skus = skus` lines
3. **Core/orchestrator_setup.py** — Replace the cache-check block with the original direct `await client.subscribed_skus.get()` call

---

## RISK ASSESSMENT

- **Risk Level:** Low
- **Affected files:** 3 files
- **Behavioral change:** `subscribed_skus.get()` is now called once (in analyze_service_plans) instead of twice. The second consumer reuses the cached response.
- **Side effects:** None — if analyze_service_plans didn't run (e.g. no graph services), `_cached_subscribed_skus` stays None and setup_graph_and_licenses falls back to the direct call.

# Change Activity: Fix Entra Internet Access & Private Access Recommendations

- **Start**: 2026-05-14 14:30
- **End**: PENDING
- **Scope**: Entra Global Secure Access recommendation modules + data collector
- **Reason**: 403 from `/beta/networkAccess/` APIs is incorrectly classified as "PermissionDenied" when it actually means the service is not activated in the tenant. Admin consent IS granted (verified live via `Get-MgServicePrincipalOAuth2PermissionGrant`). The recommendation text also hardcodes "service principal" which is wrong for interactive/device_code auth mode.

---

## Files Changed

### 1. `Core/get_entra_client.py` (lines 1102-1110)

#### BEFORE:
```python
        except httpx.HTTPStatusError as e:
            # HTTP error from beta API
            if e.response.status_code == 403:
                client_obj.network_access_summary['status'] = 'PermissionDenied'
                client_obj.network_access_summary['error'] = 'NetworkAccessPolicy.Read.All permission required'
                client_obj.private_access_summary['status'] = 'PermissionDenied'
                client_obj.private_access_summary['error'] = 'NetworkAccessPolicy.Read.All permission required'
                with _stdout_lock:
                    print(f"[{get_timestamp()}] ℹ️     Entra: Global Secure Access API access denied (requires NetworkAccessPolicy.Read.All permission)")
```

#### AFTER:
```python
        except httpx.HTTPStatusError as e:
            # HTTP error from beta API
            if e.response.status_code == 403:
                # 403 can mean either: (a) permission not granted, or (b) GSA not onboarded.
                # Distinguish by checking the error code in the response body.
                error_code = ''
                try:
                    error_body = e.response.json()
                    error_code = error_body.get('error', {}).get('code', '')
                except Exception:
                    pass
                if error_code == 'Authorization_RequestDenied':
                    client_obj.network_access_summary['status'] = 'PermissionDenied'
                    client_obj.network_access_summary['error'] = 'NetworkAccessPolicy.Read.All permission required'
                    client_obj.private_access_summary['status'] = 'PermissionDenied'
                    client_obj.private_access_summary['error'] = 'NetworkAccessPolicy.Read.All permission required'
                    with _stdout_lock:
                        print(f"[{get_timestamp()}] ℹ️     Entra: Global Secure Access API permission denied (NetworkAccessPolicy.Read.All not granted)")
                else:
                    # Non-authorization 403 means the service is not activated/licensed
                    client_obj.network_access_summary['status'] = 'NotLicensed'
                    client_obj.network_access_summary['error'] = 'Global Secure Access not activated in tenant'
                    client_obj.private_access_summary['status'] = 'NotLicensed'
                    client_obj.private_access_summary['error'] = 'Global Secure Access not activated in tenant'
                    with _stdout_lock:
                        print(f"[{get_timestamp()}] ℹ️     Entra: Global Secure Access not activated in tenant (API returned 403 — service not onboarded)")
```

---

### 2. `Recommendations/entra/ENTRA_INTERNET_ACCESS.py` (lines 82-95)

#### BEFORE:
```python
        elif network_status == 'PermissionDenied':
            # Generate permission recommendation
            observations.append(new_recommendation(
                service="Entra",
                feature=feature_name,
                observation="NetworkAccessPolicy.Read.All permission is not granted to the service principal",
                recommendation="Grant the NetworkAccessPolicy.Read.All API permission to enable Global Secure Access monitoring. This permission allows the tool to assess your web content filtering policies, traffic forwarding rules, and AI security controls. Run the setup-service-principal.ps1 script to configure required permissions, then rerun this assessment to generate Global Secure Access observations.",
                link_text="NetworkAccessPolicy Permission Reference",
                link_url="https://learn.microsoft.com/graph/permissions-reference#networkaccesspolicyreadall",
                priority="Low",
                status="Permission Required"
            ))
            return observations
```

#### AFTER:
```python
        elif network_status == 'PermissionDenied':
            # Generate auth-mode-aware permission recommendation
            import os
            auth_mode = os.getenv('AUTH_MODE', 'service_principal')
            if auth_mode == 'interactive':
                obs_text = "NetworkAccessPolicy.Read.All permission is not effective for the app registration"
                rec_text = ("Grant admin consent for the NetworkAccessPolicy.Read.All permission on the Stream 1 app registration. "
                            "Run setup-interactive-auth.ps1 to reconfigure permissions, or grant consent manually in Azure Portal > "
                            "App registrations > API permissions > Grant admin consent. Then rerun this assessment.")
            else:
                obs_text = "NetworkAccessPolicy.Read.All permission is not granted to the service principal"
                rec_text = ("Grant the NetworkAccessPolicy.Read.All application permission to the service principal. "
                            "Run setup-service-principal.ps1 to configure required permissions, then rerun this assessment.")
            observations.append(new_recommendation(
                service="Entra",
                feature=feature_name,
                observation=obs_text,
                recommendation=rec_text,
                link_text="NetworkAccessPolicy Permission Reference",
                link_url="https://learn.microsoft.com/graph/permissions-reference#networkaccesspolicyreadall",
                priority="Low",
                status="Permission Required"
            ))
            return observations
```

---

### 3. `Recommendations/entra/ENTRA_PRIVATE_ACCESS.py` (lines 64-72)

#### BEFORE:
```python
        elif private_status == 'PermissionDenied':
            observations.append(new_recommendation(
                service="Entra",
                feature=feature_name,
                observation="NetworkAccessPolicy.Read.All permission is not granted to the service principal",
                recommendation="Grant the NetworkAccessPolicy.Read.All API permission to enable Global Secure Access monitoring for both Internet and Private Access features.",
                link_text="NetworkAccessPolicy Permission Reference",
                link_url="https://learn.microsoft.com/graph/permissions-reference#networkaccesspolicyreadall",
                priority="Low",
                status="Permission Required"
            ))
```

#### AFTER:
```python
        elif private_status == 'PermissionDenied':
            import os
            auth_mode = os.getenv('AUTH_MODE', 'service_principal')
            if auth_mode == 'interactive':
                obs_text = "NetworkAccessPolicy.Read.All permission is not effective for the app registration"
                rec_text = ("Grant admin consent for the NetworkAccessPolicy.Read.All permission on the Stream 1 app registration. "
                            "Run setup-interactive-auth.ps1 to reconfigure, or grant consent in Azure Portal > App registrations > API permissions.")
            else:
                obs_text = "NetworkAccessPolicy.Read.All permission is not granted to the service principal"
                rec_text = ("Grant the NetworkAccessPolicy.Read.All application permission to the service principal. "
                            "Run setup-service-principal.ps1 to configure required permissions.")
            observations.append(new_recommendation(
                service="Entra",
                feature=feature_name,
                observation=obs_text,
                recommendation=rec_text,
                link_text="NetworkAccessPolicy Permission Reference",
                link_url="https://learn.microsoft.com/graph/permissions-reference#networkaccesspolicyreadall",
                priority="Low",
                status="Permission Required"
            ))
```

---

## Rollback Instructions

To revert all changes, replace the AFTER blocks with the BEFORE blocks in each file:
1. `Core/get_entra_client.py` — restore 403 handler to set `'PermissionDenied'`
2. `Recommendations/entra/ENTRA_INTERNET_ACCESS.py` — restore hardcoded service principal text
3. `Recommendations/entra/ENTRA_PRIVATE_ACCESS.py` — restore hardcoded service principal text

"""Service pipeline functions for orchestrator."""

import asyncio
import os
from .spinner import get_timestamp, _stdout_lock
from .orchestrator_powershell import collect_purview_data_via_powershell


def create_pipelines(client, services_and_licenses, tenant_id, service_config):
    """Create all service pipeline functions with shared context.
    
    Args:
        client: Microsoft Graph client
        services_and_licenses: ServicesAndLicenses container
        tenant_id: Azure tenant ID
        service_config: Dict with run_* flags from validate_and_prepare_services()
        
    Returns:
        Dict of pipeline functions keyed by service name
    """
    # Extract flags for easier access
    run_m365 = service_config['run_m365']
    run_entra = service_config['run_entra']
    run_defender = service_config['run_defender']
    run_purview = service_config['run_purview']
    run_power_platform = service_config['run_power_platform']
    run_copilot_studio = service_config['run_copilot_studio']
    run_a365 = service_config['run_a365']
    
    # Define pipeline functions as closures over shared context
    async def m365_pipeline():
        """M365: Gather client data, then process"""
        if not run_m365:
            return ([], [])
        
        try:
            # Gathering phase (has its own progress bar inside get_m365_client)
            from .get_m365_client import get_m365_client
            m365_client = await get_m365_client(client)
            
            # Processing phase with progress bar
            import sys
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   M365 Data Processing    [░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_m365_info import get_m365_info
            result = await get_m365_info(client, services_and_licenses, m365_client)
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ M365 Data Processing    [████████████████████] 100%\n')
                sys.stdout.flush()
            
            return result
        except Exception as e:
            import traceback
            print(f"\n[ERROR] M365 pipeline failed: {e}")
            traceback.print_exc()
            return ([], [])
    
    async def entra_pipeline():
        """Entra: Gather client data, then process"""
        if not run_entra:
            return {'available': False, 'recommendations': []}
        
        try:
            # Gathering phase (has its own progress bar inside get_entra_client)
            from .get_entra_client import get_entra_client
            entra_client = await get_entra_client(client, tenant_id)
            
            # Processing phase with progress bar
            import sys
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   Entra Data Processing   [░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_entra_info import get_entra_info
            result = await get_entra_info(client, services_and_licenses, entra_client)
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Entra Data Processing   [████████████████████] 100%\n')
                sys.stdout.flush()
            
            return result
        except Exception as e:
            return {'available': False, 'recommendations': []}
    
    async def purview_pipeline():
        """Purview: Gather client data, then process"""
        if not run_purview:
            return {'available': False, 'recommendations': []}
        
        try:
            # Check if Purview data is available from stdin
            purview_data_source = os.environ.get('PURVIEW_DATA_SOURCE')
            
            # If data not available via stdin, invoke PowerShell to collect it
            if purview_data_source != 'stdin':
                # Gathering phase - invoke PowerShell
                collection_success = await collect_purview_data_via_powershell()
                if not collection_success:
                    return {'available': False, 'recommendations': []}
            else:
                # Data available via stdin - normal path
                with _stdout_lock:
                    import sys
                    sys.stdout.write(f'\r[{get_timestamp()}]   Purview Data Gathering  [░░░░░░░░░░░░░░░░░░░░]   0%')
                    sys.stdout.flush()
            
            from .get_purview_client import get_purview_client
            purview_client = await get_purview_client(client)
            
            if purview_data_source == 'stdin':
                with _stdout_lock:
                    import sys
                    sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Purview Data Gathering  [████████████████████] 100%\n')
                    sys.stdout.flush()
            
            if purview_client is None:
                return {'available': False, 'recommendations': []}
            
            # Processing phase
            with _stdout_lock:
                import sys
                sys.stdout.write(f'\r[{get_timestamp()}]   Purview Data Processing [░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_purview_info import get_purview_info
            result = await get_purview_info(client, services_and_licenses, purview_client)
            
            with _stdout_lock:
                import sys
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Purview Data Processing [████████████████████] 100%\n')
                sys.stdout.flush()
            
            return result
        except Exception as e:
            return {'available': False, 'recommendations': []}
    
    async def defender_pipeline():
        """Defender: Gather client data, then process"""
        if not run_defender:
            return {'available': False, 'recommendations': []}
        
        try:
            # Gathering phase
            import sys
            
            from .get_defender_client import get_defender_client
            defender_client = await get_defender_client(tenant_id, client)
            
            if defender_client is None:
                return {'available': False, 'recommendations': []}
            
            # Processing phase
            with _stdout_lock:
                sys.stdout.write(f'[{get_timestamp()}]   Defender Data Processing[░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_defender_info import get_defender_info
            purview_client_for_defender = None
            result = await get_defender_info(client, defender_client, services_and_licenses, purview_client_for_defender)
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Defender Data Processing[████████████████████] 100%\n')
                sys.stdout.flush()
            
            return result
        except Exception as e:
            with _stdout_lock:
                print(f"[{get_timestamp()}] ERROR in defender_pipeline: {str(e)}")
                import traceback
                traceback.print_exc()
            return {'available': False, 'recommendations': []}
    
    async def power_platform_pipeline():
        """Power Platform: Gather client data, then process"""
        if not run_power_platform:
            return {'available': False, 'recommendations': []}
        
        try:
            # Data already collected in pre-flight (or not available)
            # Just gather and process
            import sys
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   Power Platform Gathering[░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_power_platform_client import get_power_platform_client
            pp_client = await get_power_platform_client(tenant_id)
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Power Platform Gathering[████████████████████] 100%\n')
                sys.stdout.flush()
            
            if pp_client is None:
                with _stdout_lock:
                    sys.stdout.write(f'[{get_timestamp()}]   ⚠️  Power Platform client returned None - check permissions or authentication\n')
                    sys.stdout.flush()
                return {'available': False, 'recommendations': []}
            
            # Processing phase
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   Power Platform Processing[░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_power_platform_info import get_power_platform_info
            result = await get_power_platform_info(client, services_and_licenses, pp_client)
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Power Platform Processing[████████████████████] 100%\n')
                sys.stdout.flush()
            
            return result
        except Exception as e:
            with _stdout_lock:
                sys.stdout.write(f'[{get_timestamp()}]   ✗ Power Platform pipeline error: {type(e).__name__}: {e}\n')
                sys.stdout.flush()
            import traceback
            traceback.print_exc()
            return {'available': False, 'recommendations': []}
    
    async def copilot_studio_pipeline():
        """Copilot Studio: Gather client data (reuses PP client), then process"""
        if not run_copilot_studio:
            return {'available': False, 'recommendations': []}
        
        try:
            # Gathering phase (uses same data as Power Platform from pre-flight)
            import sys
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   Copilot Studio Gathering[░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_power_platform_client import get_power_platform_client
            pp_client = await get_power_platform_client(tenant_id)
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Copilot Studio Gathering[████████████████████] 100%\n')
                sys.stdout.flush()
            
            # pp_client can be None (no enrichment data) - that's OK!
            # get_copilot_studio_info will generate basic recommendations from Graph API
            
            # Processing phase
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   Copilot Studio Processing[░░░░░░░░░░░░░░░░░░░░]   0%')
                sys.stdout.flush()
            
            from .get_copilot_studio_info import get_copilot_studio_info
            result = await get_copilot_studio_info(client, services_and_licenses, pp_client)
            
            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ Copilot Studio Processing[████████████████████] 100%\n')
                sys.stdout.flush()
            
            return result
        except Exception as e:
            with _stdout_lock:
                sys.stdout.write(f'[{get_timestamp()}]   ✗ Copilot Studio pipeline error: {type(e).__name__}: {e}\n')
                sys.stdout.flush()
            import traceback
            traceback.print_exc()
            return {'available': False, 'recommendations': []}

    async def a365_pipeline():
        """A365: Gather catalog and package details, then process both."""
        if not run_a365:
            return {'available': False, 'recommendations': []}

        try:
            import sys

            # --- Phase 1: Catalog fetch + Per-package detail fetch ---
            from .a365.get_a365_client import get_a365_client
            a365_client = await get_a365_client(tenant_id)

            if a365_client is None:
                return {'available': False, 'recommendations': []}

            # Extract token and package IDs for detail fetch.
            # Only P_* IDs are package-backed entries with full metadata support.
            # T_* IDs are title/template/internal registry entries (preview-only,
            # no detail endpoint support) and are intentionally excluded.
            access_token = a365_client.get("_access_token") or ""
            catalog_values = a365_client.get("value", []) if isinstance(a365_client.get("value", []), list) else []
            api_total_agents = a365_client.get("@odata.count")
            if not isinstance(api_total_agents, int):
                try:
                    api_total_agents = int(api_total_agents)
                except Exception:
                    api_total_agents = len(catalog_values)
            package_ids = [
                p.get("id") for p in catalog_values
                if isinstance(p, dict) and p.get("id") and p.get("id", "").startswith("P_")
            ]
            progress_total_agents = max(api_total_agents, len(package_ids))
            non_detailable_agents = max(0, progress_total_agents - len(package_ids))

            last_detail_percent = -1

            def update_detail_progress(done, total):
                nonlocal last_detail_percent
                display_done = min(progress_total_agents, done + non_detailable_agents)
                display_total = progress_total_agents
                if display_total <= 0:
                    percent = 100
                    filled = 20
                else:
                    ratio = display_done / display_total
                    percent = int(ratio * 100)
                    filled = int(ratio * 20)
                    if display_done > 0 and percent == 0:
                        percent = 1
                    if display_done > 0 and filled == 0:
                        filled = 1
                    if display_done >= display_total:
                        percent = 100
                        filled = 20
                if display_done not in (0, display_total) and percent == last_detail_percent:
                    return
                last_detail_percent = percent
                bar = '█' * filled + '░' * (20 - filled)
                counts = f'({display_done}/{display_total} Agents)' if display_total > 0 else '(0/0 Agents)'
                line = f'[{get_timestamp()}]   A365 Data Gathering     [{bar}] {percent:3d}% {counts}'
                with _stdout_lock:
                    if display_done >= display_total:
                        sys.stdout.write(f'\r[{get_timestamp()}]   ✓ A365 Data Gathering     [████████████████████] 100% {counts}\n')
                    else:
                        sys.stdout.write('\r' + line)
                    sys.stdout.flush()

            # Show initial gathering line once, then update in place.
            update_detail_progress(0, progress_total_agents)

            from .a365.get_a365_detail_client import get_a365_details
            details = await get_a365_details(
                access_token,
                package_ids,
                progress_callback=update_detail_progress,
                silent=True,
                api_total_agents=api_total_agents,
            )

            # --- Phase 2: Processing ---
            processing_percent = 0
            processing_active = True

            def write_processing_line(percent):
                clamped = max(0, min(100, int(percent)))
                filled = int(clamped * 20 / 100)
                bar = '█' * filled + '░' * (20 - filled)
                with _stdout_lock:
                    sys.stdout.write(
                        f'\r[{get_timestamp()}]   A365 Data Processing    [{bar}] {clamped:3d}%'.ljust(100)
                    )
                    sys.stdout.flush()

            async def update_processing_progress():
                nonlocal processing_percent, processing_active
                while processing_active:
                    # Keep the line moving while long-running AI summarization is in progress.
                    if processing_percent < 95:
                        processing_percent += 1
                        write_processing_line(processing_percent)
                    await asyncio.sleep(0.35)

            write_processing_line(0)
            processing_task = asyncio.create_task(update_processing_progress())

            from .a365.get_a365_info import get_a365_info
            catalog_result = await get_a365_info(a365_client)
            processing_percent = max(processing_percent, 55)
            write_processing_line(processing_percent)

            from .a365.get_a365_detail_info import get_a365_detail_info
            detail_result = await get_a365_detail_info(details)

            processing_percent = max(processing_percent, 90)
            write_processing_line(processing_percent)
            processing_active = False
            processing_task.cancel()

            with _stdout_lock:
                sys.stdout.write(f'\r[{get_timestamp()}]   ✓ A365 Data Processing    [████████████████████] 100%\n')
                sys.stdout.flush()

            # Catalog summary rows first, then detail rows.
            combined_recs = (
                catalog_result.get("recommendations", [])
                + detail_result.get("recommendations", [])
            )
            return {**catalog_result, "recommendations": combined_recs}

        except Exception:
            return {'available': False, 'recommendations': []}
    
    # Return dict of pipelines
    return {
        'm365': m365_pipeline,
        'entra': entra_pipeline,
        'purview': purview_pipeline,
        'defender': defender_pipeline,
        'power_platform': power_platform_pipeline,
        'copilot_studio': copilot_studio_pipeline,
        'a365': a365_pipeline
    }

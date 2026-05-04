"""
Command-line argument parser for the Assessment Tool.
"""

import argparse


def parse_arguments(tenant_id_default, services_default):
    """
    Parse command-line arguments for the assessment tool.
    
    Args:
        tenant_id_default: Default tenant ID from params.py
        services_default: Default services list from params.py
        
    Returns:
        argparse.Namespace: Parsed arguments with tenant_id and services
    """
    parser = argparse.ArgumentParser(
        description='Microsoft 365 Copilot and Agents Readiness Assessment Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py
  python main.py --services M365
    python main.py --services A365
  python main.py --services M365 Entra Defender
  python main.py --tenant-id "your-tenant-id" --services Purview
        '''
    )
    parser.add_argument(
        '--tenant-id', 
        type=str, 
        default=tenant_id_default,
        help=f'Tenant ID to analyze (default: {tenant_id_default})'
    )
    parser.add_argument(
        '--services', 
        nargs='*', 
        default=services_default,
        help=f'Services to analyze: M365, Entra, Defender, Purview, "Power Platform", "Copilot Studio", A365 (default: {services_default or "all services"})'
    )
    parser.add_argument(
        '--auth-mode',
        type=str,
        choices=['service_principal', 'interactive'],
        default=None,
        help='Authentication mode: service_principal (default) or interactive (browser login with MFA). Can also be set via AUTH_MODE in .env'
    )
    
    args = parser.parse_args()
    
    # If --auth-mode not provided on CLI, check AUTH_MODE env var
    if args.auth_mode is None:
        import os
        args.auth_mode = os.environ.get('AUTH_MODE', 'service_principal')
    
    # Set AUTH_MODE in environment for downstream modules
    import os
    os.environ['AUTH_MODE'] = args.auth_mode
    
    return args

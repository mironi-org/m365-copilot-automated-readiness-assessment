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

  # Interactive browser authentication (no client secret needed):
    python main.py --auth-mode interactive
    python main.py --auth-mode interactive --services M365 Entra
    python main.py --auth-mode interactive --services Defender

        # Device code authentication (assessment step only, not for setup):
        # (Do NOT use device_code with setup-interactive-auth.ps1)
        python main.py --auth-mode device_code
        python main.py --auth-mode device_code --services M365 Entra
        python main.py --auth-mode device_code --services Defender
        python main.py --auth-mode device_code --services Purview
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
        choices=['service_principal', 'interactive', 'device_code'],
        default=None,
        help='Authentication mode: service_principal (default), interactive (browser login with MFA), or device_code (enter code at verification URL, assessment step only — NOT for setup). Can also be set via AUTH_MODE in .env'
    )
    
    args = parser.parse_args()
    
    # If --auth-mode not provided on CLI, check AUTH_MODE env var
    if args.auth_mode is None:
        import os
        args.auth_mode = os.environ.get('AUTH_MODE', 'service_principal')
    
    # Device code is a variant of interactive auth — map it internally
    # so all downstream code only checks AUTH_MODE == 'interactive'
    import os
    if args.auth_mode == 'device_code':
        os.environ['AUTH_MODE'] = 'interactive'
        os.environ['USE_DEVICE_CODE'] = '1'
    else:
        os.environ['AUTH_MODE'] = args.auth_mode
    
    return args

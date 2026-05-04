"""
Credential validation for Azure/Microsoft 365 authentication.
Checks for required environment variables before starting orchestration.
"""
import os
import sys


def load_env_file(base_path=None):
    """Load .env file if it exists.
    
    Args:
        base_path: Base path to look for .env file. If None, uses parent of Core folder.
    """
    if base_path is None:
        base_path = os.path.dirname(os.path.dirname(__file__))
    
    env_path = os.path.join(base_path, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def check_credentials():
    """Check if required environment variables are set.
    
    Returns:
        list: List of missing variable names, empty if all present.
    """
    # Load .env file first
    load_env_file()
    
    auth_mode = os.environ.get('AUTH_MODE', 'service_principal')
    
    # Check required variables
    missing = []
    if not os.environ.get('TENANT_ID'):
        missing.append('TENANT_ID')
    if not os.environ.get('CLIENT_ID'):
        missing.append('CLIENT_ID')
    # CLIENT_SECRET is only required for service_principal mode
    if auth_mode != 'interactive' and not os.environ.get('CLIENT_SECRET'):
        missing.append('CLIENT_SECRET')
    
    return missing


def validate_credentials_or_exit(get_timestamp_func):
    """Validate credentials and exit with helpful message if missing.
    
    Args:
        get_timestamp_func: Function to get formatted timestamp for messages.
    """
    missing_vars = check_credentials()
    if missing_vars:
        print(f"[{get_timestamp_func()}] ❌ Missing required credentials: {', '.join(missing_vars)}")
        print()
        print("To use this tool, you need to configure Azure credentials:")
        print("  Option 1 (Service Principal): Run .\\setup-service-principal.ps1")
        print("  Option 2 (Interactive Browser): Run .\\setup-interactive-auth.ps1")
        print("           then use: python main.py --auth-mode interactive")
        print()
        print("See RUN.md for detailed setup instructions.")
        sys.exit(1)

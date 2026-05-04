"""GitHub CLI installation and authentication setup for A365."""

import subprocess
import sys
from Core.spinner import get_timestamp


def _is_github_cli_installed():
    """Check if GitHub CLI is installed."""
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _is_github_cli_authenticated():
    """Check if GitHub CLI is authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _install_github_cli():
    """Attempt to install GitHub CLI using available package managers."""
    print(f"\n[{get_timestamp()}] Installing GitHub CLI...")
    
    # Try Chocolatey first (Windows)
    try:
        result = subprocess.run(
            ["choco", "install", "gh", "-y"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0:
            print(f"[{get_timestamp()}] ✓ GitHub CLI installed via Chocolatey")
            return True
    except Exception:
        pass
    
    # Try winget (Windows)
    try:
        result = subprocess.run(
            ["winget", "install", "--id", "GitHub.cli"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0:
            print(f"[{get_timestamp()}] ✓ GitHub CLI installed via winget")
            return True
    except Exception:
        pass
    
    # Manual installation instructions
    print(f"\n[{get_timestamp()}] ⚠️  GitHub CLI installation failed or not available via package managers.")
    print(f"[{get_timestamp()}] Please install GitHub CLI manually:")
    print(f"[{get_timestamp()}]   Windows (Chocolatey): choco install gh")
    print(f"[{get_timestamp()}]   Windows (winget):     winget install --id GitHub.cli")
    print(f"[{get_timestamp()}]   macOS (Homebrew):     brew install gh")
    print(f"[{get_timestamp()}]   Linux:                https://cli.github.com/manual/installation")
    return False


def _authenticate_github_cli():
    """Prompt user to authenticate GitHub CLI."""
    print(f"\n[{get_timestamp()}] Authenticating with GitHub...")
    print(f"[{get_timestamp()}] Opening browser for GitHub authentication...")
    
    try:
        result = subprocess.run(
            ["gh", "auth", "login", "-p", "https", "-w"],
            capture_output=False,
            text=True,
            timeout=300,
            check=False,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[{get_timestamp()}] ⚠️  Authentication failed: {e}")
        return False


def ensure_github_cli_ready():
    """Ensure GitHub CLI is installed and authenticated.
    
    Returns:
        bool: True if GitHub CLI is ready, False otherwise.
    """
    # Check if already installed
    if not _is_github_cli_installed():
        print(f"\n[{get_timestamp()}] GitHub CLI not found. GitHub Copilot is required for A365.")
        
        # Attempt installation
        if not _install_github_cli():
            print(f"\n[{get_timestamp()}] ❌ Failed to install GitHub CLI. A365 requires GitHub Copilot API access.")
            return False
    else:
        print(f"[{get_timestamp()}] ✓ GitHub CLI is installed")
    
    # Check if authenticated
    if not _is_github_cli_authenticated():
        print(f"\n[{get_timestamp()}] GitHub CLI is not authenticated.")
        
        # Attempt authentication
        if not _authenticate_github_cli():
            print(f"\n[{get_timestamp()}] ❌ GitHub CLI authentication failed. A365 requires authenticated GitHub Copilot access.")
            return False
    else:
        print(f"[{get_timestamp()}] ✓ GitHub CLI is authenticated")
    
    print(f"[{get_timestamp()}] ✓ GitHub CLI ready for A365")
    return True

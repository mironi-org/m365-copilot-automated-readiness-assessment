TENANT_ID = "0b5085b5-bea9-47a1-a6d2-d35a27943123"  # e.g., 'contoso.onmicrosoft.com' or GUID

# Services to analyze - valid values: "M365", "Entra", "Defender", "Purview", "Power Platform", "Copilot Studio", "A365"
# Empty array = analyze all services
# Note: "Defender" includes Copilot-specific security recommendations (Security Posture, Threat Intelligence, Data Governance)
#       Copilot Data Governance recommendation will also use Purview data if available (run with: .\collect_purview_data.ps1)
SERVICES = []  # e.g., ["M365", "Entra"], ["Defender", "Purview"], or [] for all
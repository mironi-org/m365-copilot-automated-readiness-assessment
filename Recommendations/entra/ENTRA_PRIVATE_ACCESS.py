"""
Microsoft Entra Private Access - Copilot & Agent Adoption Recommendation
"""
from Core.new_recommendation import new_recommendation
from Core.friendly_names import get_friendly_sku_name

def get_recommendation(sku_name, status="Success", client=None, entra_insights=None):
    """
    Entra Private Access provides zero-trust network access to
    internal resources that Copilot and agents need to access securely.
    
    Args:
        sku_name: SKU name where the feature is found
        status: Provisioning status
        client: Optional Graph client (not used - data comes from entra_insights)
        entra_insights: Dict containing pre-computed private access metrics
    
    Returns:
        list: List of recommendation objects
    """
    feature_name = "Microsoft Entra Private Access"
    friendly_sku = get_friendly_sku_name(sku_name)
    observations = []
    
    # License check observation
    if status == "Success":
        observations.append(new_recommendation(
            service="Entra",
            feature=feature_name,
            observation=f"{feature_name} is active in {friendly_sku}, enabling secure zero-trust access to private resources for AI workloads",
            recommendation="",
            link_text="Zero-Trust Network for AI",
            link_url="https://learn.microsoft.com/entra/global-secure-access/",
            status=status
        ))
    else:
        observations.append(new_recommendation(
            service="Entra",
            feature=feature_name,
            observation=f"{feature_name} is {status} in {friendly_sku}, limiting secure access to internal data sources for Copilot",
            recommendation=f"Enable {feature_name} to provide zero-trust network access to on-premises and private cloud resources that Copilot and custom agents need to query. Private Access eliminates VPN requirements while enforcing per-app access controls and continuous verification. Deploy agents that securely access internal databases, legacy systems, and private APIs without exposing them to the internet. Essential for extending Copilot's knowledge to include proprietary systems while maintaining zero-trust security posture.",
            link_text="Zero-Trust Network for AI",
            link_url="https://learn.microsoft.com/entra/global-secure-access/",
            priority="Medium",
            status=status
        ))
    
    # Configuration observation (if entra_insights available)
    if entra_insights:
        private_summary = entra_insights.get('private_access_summary', {})
        private_status = private_summary.get('status')
        
        if private_status == 'NotLicensed':
            observations.append(new_recommendation(
                service="Entra",
                feature=feature_name,
                observation="Global Secure Access (Entra Private Access) is not enabled in your tenant",
                recommendation="Enable Global Secure Access Private Access to provide secure zero-trust connectivity to internal applications for Copilot and custom agents. This allows AI assistants to access on-premises databases, legacy LOB systems, and private cloud resources without VPN while maintaining granular access controls. Essential for extending Copilot beyond M365 data to include proprietary business systems.",
                link_text="What is Global Secure Access?",
                link_url="https://learn.microsoft.com/entra/global-secure-access/overview-what-is-global-secure-access",
                priority="Medium",
                status="Not Licensed"
            ))
        elif private_status == 'AccessDenied':
            # Non-permission 403 — service not activated or directory role insufficient
            error_detail = private_summary.get('error', 'Unknown')
            observations.append(new_recommendation(
                service="Entra",
                feature=feature_name,
                observation=f"Global Secure Access (Private Access) API returned HTTP 403 ({error_detail})",
                recommendation="The Global Secure Access API returned HTTP 403. This typically means "
                               "Global Secure Access is not activated or licensed in your tenant. "
                               "If the service is activated, ensure the signed-in user has the "
                               "Global Secure Access Administrator directory role (or Global Administrator). "
                               "A Global Reader role alone is not sufficient for this API.",
                link_text="Global Secure Access Prerequisites",
                link_url="https://learn.microsoft.com/entra/global-secure-access/overview-what-is-global-secure-access",
                priority="Low",
                status="Access Denied"
            ))
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
        elif private_status == 'Success':
            total_connectors = private_summary.get('total_connectors', 0)
            active_connectors = private_summary.get('active_connectors', 0)
            total_apps = private_summary.get('total_apps', 0)
            
            if total_connectors > 0:
                observations.append(new_recommendation(
                    service="Entra",
                    feature=feature_name,
                    observation=f"Private Access configured: {total_connectors} connector(s) deployed ({active_connectors} active), {total_apps} application segment(s) published for zero-trust AI access to internal resources",
                    recommendation="",
                    link_text="Manage Private Access",
                    link_url="https://learn.microsoft.com/entra/global-secure-access/how-to-configure-connectors",
                    status=status
                ))
            else:
                observations.append(new_recommendation(
                    service="Entra",
                    feature=feature_name,
                    observation="Private Access licensed but no connectors deployed to enable AI access to internal resources",
                    recommendation="Deploy Private Access connectors to enable Copilot and custom agents to securely access on-premises applications, databases, and APIs. Configure application segments for resources that AI needs to query (SharePoint on-premises, SQL databases, ERP systems, CRM platforms). This extends Copilot's knowledge beyond cloud data while maintaining zero-trust controls.",
                    link_text="Deploy Private Access Connectors",
                    link_url="https://learn.microsoft.com/entra/global-secure-access/how-to-configure-connectors",
                    priority="Medium",
                    status=status
                ))
    
    return observations

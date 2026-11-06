"""
Mounts the FastMCP server as a Django URL route.
The FastMCP HTTP transport exposes the MCP protocol at /mcp/.
"""

from django.urls import path
from django.http import JsonResponse


def mcp_health(request):
    """Simple health check for the MCP server."""
    return JsonResponse(
        {
            "status": "ok",
            "server": "TalentPulse MCP",
            "tools": ["github_researcher", "culture_fit_check", "email_sender"],
        }
    )


# FastMCP exposes an ASGI/WSGI app — wrap it for Django URL routing
# In production, you can run the MCP server as a separate process.
# For development, expose it via a health endpoint.
urlpatterns = [
    path("health/", mcp_health, name="mcp-health"),
]
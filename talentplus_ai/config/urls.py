from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def health(_request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("health/", health),
    path("admin/", admin.site.urls),
    path("docs", lambda request: redirect("/api/schema/swagger-ui/")),
    path("docs/", lambda request: redirect("/api/schema/swagger-ui/")),

    # ── Session auth (SPA) ───────────────────────────────────────
    path("api/auth/", include("talentplus_ai.users.api.auth_urls")),

    # ── Application APIs ───────────────────────────────────────
    path("api/candidates/", include("talentplus_ai.candidates.urls")),
    path("api/agent/", include("talentplus_ai.agent.urls")),
    path("api/dashboard/", include("talentplus_ai.dashboard.urls")),
    path("api/ragchat/", include("talentplus_ai.ragchat.urls")),
    path("api/voice/", include("talentplus_ai.voice.urls")),

    # ── MCP Protocol ───────────────────────────────────────────
    path("mcp/", include("talentplus_ai.mcp_tools.urls")),

    # ── OpenAPI Schema + Swagger UI ────────────────────────────
    # /api/schema/             → raw OpenAPI JSON schema
    # /api/schema/swagger-ui/  → Swagger interactive docs
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-swagger",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
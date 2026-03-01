"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

from rest_framework.permissions import AllowAny
from rest_framework.schemas import get_schema_view
from rest_framework.renderers import JSONOpenAPIRenderer


schema_view = get_schema_view(
    title="Service A API",
    public=True,
    permission_classes=[AllowAny],
    authentication_classes=[],
    renderer_classes=[JSONOpenAPIRenderer],
)


def healthz(request):
    return JsonResponse({"status": "ok", "service": "A"})


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    # Development-only OpenAPI schema
    # (No auth in development; omitted in production)
    *(
        [
            path("api/schema/", schema_view, name="api-schema"),
            path("schema/", schema_view, name="schema"),
        ]
        if getattr(settings, "ENVIRONMENT", "development") == "development" or settings.DEBUG
        else []
    ),
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("projects.urls")),
    path("api/", include("analysis.urls")),
]

# Serve uploaded files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


  




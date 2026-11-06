"""Session-based auth API for SPA (Option A: Django sessions).

See Django auth: https://docs.djangoproject.com/en/stable/topics/auth/default/
CSRF for AJAX: https://docs.djangoproject.com/en/stable/ref/csrf/
DRF + session: https://www.django-rest-framework.org/topics/ajax-csrf-cors/
"""

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_csrf(request):
    """Return CSRF token for unsafe requests; sets csrftoken cookie."""
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_login(request):
    """Validate email/password, create Django session.

    Only staff users may use the SPA (internal recruiter / admin tooling).
    Non-staff users get 403 so the SPA is not a second login surface for
    public or candidate accounts.
    """
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""
    if not email or not password:
        return Response({"detail": "Email and password are required."}, status=400)

    user = authenticate(request, email=email, password=password)
    if user is None:
        return Response({"detail": "Invalid email or password."}, status=400)
    if not user.is_active:
        return Response({"detail": "This account is disabled."}, status=403)
    if not user.is_staff:
        return Response({"detail": "Access restricted to admin users."}, status=403)

    login(request, user)
    return Response(
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name or "",
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            }
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """Destroy session."""
    logout(request)
    return Response(status=204)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def auth_me(request):
    """Current session user."""
    u = request.user
    return Response(
        {
            "id": u.id,
            "email": u.email,
            "name": u.name or "",
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
        }
    )

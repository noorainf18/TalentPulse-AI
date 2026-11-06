from rest_framework.permissions import BasePermission
from .models import VoiceInterview


class IsRecruiter(BasePermission):
    """
    Allow authenticated users who are staff or have recruiter role.
    Adjust to your actual user model / role field.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsCandidateSessionToken(BasePermission):
    """
    Allows access when a valid session_token is passed as a query param.
    Used by the candidate-facing interview join endpoint — candidates don't
    have Django accounts, they join via the secure link in their invite email.
    """
    def has_permission(self, request, view):
        token = request.query_params.get("token") or request.data.get("token")
        if not token:
            return False
        return VoiceInterview.objects.filter(
            session_token=token,
        ).exists()
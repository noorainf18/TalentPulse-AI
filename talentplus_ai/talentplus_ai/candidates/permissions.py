from rest_framework.permissions import BasePermission


class IsRecruiter(BasePermission):
    """
    Allows access to authenticated users who belong to the 'Recruiters' group.
    Extendable with role-based auth when Supabase Auth is integrated.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_staff
                or request.user.groups.filter(name="Recruiters").exists()
            )
        )

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allow access only to users with role=ADMIN."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "ADMIN"
        )


class IsOwnerOrAdmin(BasePermission):
    """Allow access to the object owner or an ADMIN user."""

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "role", None) == "ADMIN":
            return True
        owner = getattr(obj, "created_by", None)
        return owner == request.user

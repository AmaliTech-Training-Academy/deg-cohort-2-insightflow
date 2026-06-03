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


class IsOwner(BasePermission):
    """Allow access only to the object owner."""

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "created_by", None) or getattr(obj, "user", None)
        return owner == request.user


class IsSuperAdmin(BasePermission):
    """Allow access only to superadmin users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class IsAdminOrReadOnly(BasePermission):
    """Allow admin users to edit, others to read only."""

    def has_permission(self, request, view):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        return bool(request.user and request.user.is_staff)


class IsAuthenticatedOrReadOnly(BasePermission):
    """Allow authenticated users to write, others to read only."""

    def has_permission(self, request, view):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        return bool(request.user and request.user.is_authenticated)

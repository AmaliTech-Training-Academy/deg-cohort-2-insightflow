from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    """Throttle for login endpoint."""

    scope = "login"

    def get_ident(self, request):
        email = request.data.get("email", "")
        return email if email else request.META.get("REMOTE_ADDR", "")


class RefreshTokenThrottle(UserRateThrottle):
    """Throttle for token refresh endpoint."""

    scope = "refresh_token"

    def get_ident(self, request):
        if request.user and request.user.is_authenticated:
            return f"user_{request.user.id}"
        return request.META.get("REMOTE_ADDR", "")

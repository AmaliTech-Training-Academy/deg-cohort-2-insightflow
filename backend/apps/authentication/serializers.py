import logging
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import TokenBlacklist

User = get_user_model()
logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "role",
        ]
        read_only_fields = ["id", "is_active", "role"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "first_name",
            "last_name",
            "role",
        ]
        read_only_fields = ["role"]
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                _("Password must be at least 8 characters long.")
            )
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError(
                _("Password must contain at least one uppercase letter.")
            )
        if not any(c.islower() for c in value):
            raise serializers.ValidationError(
                _("Password must contain at least one lowercase letter.")
            )
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError(
                _("Password must contain at least one digit.")
            )
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in value):
            raise serializers.ValidationError(
                _(
                    "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)."  # noqa E501
                )
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                _("A user with this email already exists.")
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                _("A user with this username already exists.")
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(_("Invalid email or password."))

        if not user.check_password(password):
            raise serializers.ValidationError(_("Invalid email or password."))

        if not user.is_active:
            raise serializers.ValidationError(_("This user account is inactive."))

        data["user"] = user
        return data


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            RefreshToken(value)
        except Exception:
            raise serializers.ValidationError(_("Invalid or expired refresh token."))
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value):
        try:
            refresh = RefreshToken(value)
        except Exception:
            raise serializers.ValidationError(_("Invalid or expired refresh token."))

        try:
            data = refresh.token_backend.decode(value, verify=True)  # noqa F401
        except Exception:
            raise serializers.ValidationError(_("Token is invalid or expired."))

        return value

    def save(self):
        refresh_token = self.validated_data["refresh"]
        try:
            refresh = RefreshToken(refresh_token)
            data = refresh.token_backend.decode(  # noqa F401
                refresh_token, verify=False
            )
            TokenBlacklist.objects.create(
                token=refresh_token,
                user=self.context["request"].user,
                expires_at=datetime.fromtimestamp(
                    refresh.payload["exp"], tz=timezone.utc
                ),
            )
        except Exception as e:
            logger.warning("An error occurred during token processing: %s", e)

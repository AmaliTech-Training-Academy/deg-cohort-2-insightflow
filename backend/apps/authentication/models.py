from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.BigAutoField(primary_key=True, db_column="userId", default=None)
    role = models.CharField(max_length=255, db_column="role", blank=True, null=True)

    class Meta:
        db_table = "users"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta.get_field("username").db_column = "username"
        self._meta.get_field("email").db_column = "email"
        self._meta.get_field("is_active").db_column = "is_active"


class TokenBlacklist(models.Model):
    token = models.TextField()
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blacklisted_tokens"
    )
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "token_blacklist"
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "blacklisted_at"]),
        ]

    def __str__(self):
        return f"Token blacklisted for {self.user} at {self.blacklisted_at}"

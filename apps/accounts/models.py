import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from handouts.models import Handout, Section

from security.otp_generator import OTPGenerator

from .enums import Tier, UserRole
from .utils import get_avatar_upload_path


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20, choices=[(role.value, role.name) for role in UserRole], default=UserRole.EDITOR.value
    )
    avatar = models.ImageField(upload_to=get_avatar_upload_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.BETA,
    )
    last_storage_warning_level = models.IntegerField(default=0)
    current_storage_usage = models.BigIntegerField(default=0)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username

    def get_total_usage(self):
        return self.current_storage_usage

    def update_usage(self):
        pdf_usage = Handout.objects.filter(project__owner=self).aggregate(total=models.Sum("file_size"))["total"] or 0

        md_usage = (
            Section.objects.filter(handout__project__owner=self).aggregate(
                total=models.Sum(models.functions.Length("content"))
            )["total"]
            or 0
        )

        self.current_storage_usage = pdf_usage + md_usage
        self.save(update_fields=["current_storage_usage"])
        return self.current_storage_usage

    @property
    def storage_limit(self):
        return Tier(self.tier).storage_limit

    @property
    def remaining_storage(self):
        return max(0, self.storage_limit - self.get_total_usage())


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="verification_token")
    token = models.CharField(max_length=255, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        expiry = self.created_at + timezone.timedelta(hours=24)
        return not self.is_used and timezone.now() < expiry


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="custom_password_reset_tokens")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    otp = models.CharField(max_length=7)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_tokens"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = OTPGenerator.generate_strong_otp()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=30)

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

import os

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import PasswordResetToken, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "created_at",
            "tier",
            "avatar",
            "storage_limit",
            "remaining_storage",
            "current_storage_usage",
        ]
        read_only_fields = ["id", "created_at", "storage_limit", "remaining_storage", "current_storage_usage"]

    def validate_avatar(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Avatar file size must be under 5MB.")

        ext = os.path.splitext(value.name)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            raise serializers.ValidationError("Only .jpg, .jpeg, and .png files are allowed.")

        return value

    def get_remaining_storage(self, obj):
        return obj.remaining_storage

    def get_storage_limit(self, obj):
        return obj.storage_limit


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "password", "email", "first_name", "last_name", "role"]

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class ResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value


class ResetPasswordConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)
    otp = serializers.CharField(required=True, min_length=7, max_length=7)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])

    def validate(self, data):
        try:
            reset_obj = PasswordResetToken.objects.get(token=data["token"])
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid reset token."}) from None

        if not reset_obj.is_valid:
            raise serializers.ValidationError({"token": "This link has expired or been used."})

        if reset_obj.otp != data["otp"]:
            raise serializers.ValidationError({"otp": "The verification code is incorrect."})

        self.context["reset_obj"] = reset_obj
        return data


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

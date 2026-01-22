from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from drf_spectacular.utils import extend_schema
from letters.models import EmailTemplate, Letter
from letters.tasks import send_letter_task
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import EmailVerificationToken, PasswordResetToken, User
from .serializers import (
    ChangePasswordSerializer,
    RegisterSerializer,
    ResetPasswordConfirmSerializer,
    ResetPasswordEmailSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)


class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"refresh": {"type": "string"}}}},
        responses={205: None},
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save(is_active=False)
        lang = self.request.query_params.get("lang", "en-us")

        signer = TimestampSigner()
        token = signer.sign(str(user.id))

        EmailVerificationToken.objects.create(user=user, token=token)

        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        try:
            try:
                template = EmailTemplate.objects.get(name="email_verification", language=lang)
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.get(name="email_verification", language="en-us")

            letter = Letter.objects.create(
                template=template,
                recipient_email=user.email,
                context={"username": user.username, "verification_url": verification_url},
            )
            send_letter_task.delay(letter.id)
        except EmailTemplate.DoesNotExist:
            pass


class VerifyEmailView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=VerifyEmailSerializer, responses={200: None})
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token_str = serializer.validated_data.get("token")

        with transaction.atomic():
            try:
                vt = EmailVerificationToken.objects.select_for_update().get(token=token_str)
            except EmailVerificationToken.DoesNotExist:
                return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

            if vt.is_used and vt.user.is_verified:
                return Response({"status": "already_verified"}, status=status.HTTP_200_OK)

            signer = TimestampSigner()
            try:
                user_id_str = signer.unsign(token_str, max_age=86400)

                if vt.is_used:
                    return Response({"error": "Token already used"}, status=status.HTTP_400_BAD_REQUEST)

                user = vt.user

                if str(user.id) != user_id_str:
                    return Response({"error": "User ID mismatch"}, status=status.HTTP_400_BAD_REQUEST)

                user.is_active = True
                user.is_verified = True
                user.save()

                vt.is_used = True
                vt.save()

                return Response({"status": "verified"}, status=status.HTTP_200_OK)

            except SignatureExpired:
                return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)
            except BadSignature:
                return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(request=ChangePasswordSerializer, responses={200: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.data.get("new_password"))
            user.save()
            return Response({"status": "password set"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=ResetPasswordEmailSerializer, responses={200: None})
    def post(self, request):
        serializer = ResetPasswordEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        user = User.objects.get(email=email)
        lang = request.query_params.get("lang", "zh_TW")

        reset_token = PasswordResetToken.objects.create(user=user)

        try:
            language_aliases = {
                "zh_TW": ["zh-hant", "zh-tw", "zh_TW"],
                "zh_CN": ["zh-hans", "zh-cn", "zh_CN"],
                "th": ["th"],
                "en": ["en", "en-us"],
            }
            search_langs = language_aliases.get(lang, []) + language_aliases["zh_TW"] + language_aliases["en"]

            template = None
            for lang_code in search_langs:
                template = EmailTemplate.objects.filter(name="password_reset", language=lang_code).first()
                if template:
                    print(f"DEBUG: Found template: {template.name} in {lang_code}")
                    break
            if not template:
                print(f"DEBUG: No template found for name 'password_reset' in {search_langs}")

            if template:
                letter = Letter.objects.create(
                    template=template,
                    recipient_email=user.email,
                    context={
                        "username": user.username,
                        "otp": reset_token.otp,
                        "token": str(reset_token.token),
                        "reset_url": f"{settings.FRONTEND_URL}/reset-password",
                    },
                )
                send_letter_task.delay(letter.id)
        except Exception as e:
            print(f"Password reset email failed: {str(e)}")

        return Response({"detail": "Password reset email has been sent."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=ResetPasswordConfirmSerializer, responses={200: None})
    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reset_obj = serializer.context["reset_obj"]
        user = reset_obj.user

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        reset_obj.is_used = True
        reset_obj.save()

        return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)

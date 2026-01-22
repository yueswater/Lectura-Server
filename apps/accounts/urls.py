from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    ChangePasswordView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    UserDetailView,
    VerifyEmailView,
)

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("me/", UserDetailView.as_view(), name="user_me"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("password-reset/", include("django_rest_passwordreset.urls", namespace="password_reset")),
    path("password-reset-request/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EmailTemplateViewSet, LetterViewSet

router = DefaultRouter()
router.register(r"templates", EmailTemplateViewSet, basename="email-template")
router.register(r"", LetterViewSet, basename="letter")

urlpatterns = [
    path("", include(router.urls)),
]

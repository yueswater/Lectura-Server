from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttachmentViewSet, HandoutViewSet, SectionViewSet

router = DefaultRouter()
router.register(r"handouts", HandoutViewSet, basename="handout")
router.register(r"sections", SectionViewSet, basename="section")
router.register(r"attachments", AttachmentViewSet, basename="attachment")

urlpatterns = [
    path("", include(router.urls)),
]

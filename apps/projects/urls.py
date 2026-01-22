from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FolderViewSet, ProjectViewSet, TagViewSet

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"folders", FolderViewSet, basename="folder")
router.register(r"tags", TagViewSet, basename="tag")

urlpatterns = [
    path("", include(router.urls)),
]

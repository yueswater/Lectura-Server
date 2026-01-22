import io
import logging
import zipfile

from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from handouts.utils import generate_handout_pdf
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import Folder, Project, Tag
from .serializers import FolderSerializer, ProjectSerializer, TagSerializer

logger = logging.getLogger("download_zip")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tag.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema_view(
    list=extend_schema(tags=["Management - Projects"]),
    retrieve=extend_schema(tags=["Management - Projects"]),
    create=extend_schema(tags=["Management - Projects"]),
    update=extend_schema(tags=["Management - Projects"]),
    partial_update=extend_schema(tags=["Management - Projects"]),
    destroy=extend_schema(tags=["Management - Projects"]),
)
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["owner"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user).prefetch_related("tags")

    def perform_create(self, serializer):
        tag_ids = self.request.data.get("tag_ids", [])
        user_tags = Tag.objects.filter(owner=self.request.user, id__in=tag_ids)

        if len(tag_ids) != user_tags.count():
            raise serializers.ValidationError({"tag_ids": "One or more tags do not belong to you."})

        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"], url_path="download-zip")
    def download_all_handouts(self, request, pk=None):
        project = self.get_queryset().filter(pk=pk).first()

        if not project:
            return Response({"error": "Project not found or you don't have permission."}, status=404)

        handouts = project.handouts.all()
        if not handouts.exists():
            return Response({"error": "No handouts in this project."}, status=400)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for handout in handouts:
                try:
                    pdf_content = generate_handout_pdf(handout)
                    if pdf_content:
                        safe_title = "".join([c for c in handout.title if c.isalnum() or c in (" ", "-", "_")]).strip()
                        zip_file.writestr(f"{safe_title}.pdf", pdf_content)
                except Exception as e:
                    logger.error(f"Failed to add {handout.title} to zip: {str(e)}")

        zip_buffer.seek(0)
        filename = f"{project.name}_{timezone.now().strftime('%Y%m%d%H%M')}.zip"

        return FileResponse(zip_buffer, as_attachment=True, filename=filename, content_type="application/zip")


@extend_schema_view(
    list=extend_schema(tags=["Management - Folders"]),
    retrieve=extend_schema(tags=["Management - Folders"]),
    create=extend_schema(tags=["Management - Folders"]),
    update=extend_schema(tags=["Management - Folders"]),
    partial_update=extend_schema(tags=["Management - Folders"]),
    destroy=extend_schema(tags=["Management - Folders"]),
)
class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["project", "parent"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]
    ordering = ["name"]

    def get_queryset(self):
        return Folder.objects.filter(project__owner=self.request.user)

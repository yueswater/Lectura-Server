from django.db import transaction
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import exceptions, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Attachment, Handout, Section
from .serializers import AttachmentSerializer, HandoutSerializer, SectionSerializer
from .utils import generate_handout_pdf


@extend_schema_view(
    list=extend_schema(tags=["Content - Handouts"]),
    retrieve=extend_schema(tags=["Content - Handouts"]),
    create=extend_schema(tags=["Content - Handouts"]),
    update=extend_schema(tags=["Content - Handouts"]),
    partial_update=extend_schema(tags=["Content - Handouts"]),
    destroy=extend_schema(tags=["Content - Handouts"]),
)
class HandoutViewSet(viewsets.ModelViewSet):
    serializer_class = HandoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["project", "folder", "is_published"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        return Handout.objects.filter(project__owner=self.request.user)

    def perform_create(self, serializer):
        project = serializer.validated_data.get("project")
        if project.owner != self.request.user:
            raise exceptions.PermissionDenied("You do not have permission to add a handout to this project.")
        serializer.save()

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "format": "uuid"},
                                "parent_id": {"type": "string", "format": "uuid", "nullable": True},
                                "order": {"type": "integer"},
                            },
                        },
                    }
                },
            }
        },
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
        tags=["Content - Handouts"],
    )
    @action(detail=True, methods=["post"], url_path="reorder-sections")
    def reorder_sections(self, request, pk=None):
        handout = self.get_object()
        structure = request.data.get("structure", [])

        if not structure:
            return Response({"error": "No structure provided"}, status=status.HTTP_400_BAD_REQUEST)

        section_ids = [item.get("id") for item in structure]
        valid_count = Section.objects.filter(id__in=section_ids, handout=handout).count()
        if valid_count != len(section_ids):
            return Response(
                {"error": "Invalid section IDs provided for this handout"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                for item in structure:
                    s_id = item.get("id")
                    parent_id = item.get("parent_id")
                    order = item.get("order", 0)

                    parent = None
                    if parent_id:
                        parent = Section.objects.get(id=parent_id)
                        if parent.handout_id != handout.id:
                            raise exceptions.ValidationError(f"Parent {parent_id} does not belong to this handout")
                        if str(parent.id) == str(s_id):
                            continue

                    section = Section.objects.get(id=s_id)
                    section.parent = parent
                    section.order = order
                    section.save()

            return Response({"status": "sections reordered and restructured"}, status=status.HTTP_200_OK)

        except Section.DoesNotExist:
            return Response({"error": "Section not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={(200, "application/pdf"): {"type": "string", "format": "binary"}},
        tags=["Content - Handouts"],
    )
    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        handout = self.get_object()
        try:
            pdf_content = generate_handout_pdf(handout)
            return HttpResponse(pdf_content, content_type="application/pdf")
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


@extend_schema_view(
    list=extend_schema(tags=["Content - Sections"]),
    retrieve=extend_schema(tags=["Content - Sections"]),
    create=extend_schema(tags=["Content - Sections"]),
    update=extend_schema(tags=["Content - Sections"]),
    partial_update=extend_schema(tags=["Content - Sections"]),
    destroy=extend_schema(tags=["Content - Sections"]),
)
class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["handout", "parent", "level"]
    search_fields = ["title", "content"]
    ordering_fields = ["order", "created_at"]
    ordering = ["order"]

    def get_queryset(self):
        return Section.objects.filter(handout__project__owner=self.request.user)

    def perform_create(self, serializer):
        handout = serializer.validated_data.get("handout")
        if handout.project.owner != self.request.user:
            raise exceptions.PermissionDenied("You do not have permission to add a section to this handout.")
        serializer.save()


@extend_schema_view(
    list=extend_schema(tags=["Content - Attachments"]),
    retrieve=extend_schema(tags=["Content - Attachments"]),
    create=extend_schema(tags=["Content - Attachments"]),
    destroy=extend_schema(tags=["Content - Attachments"]),
)
class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    filter_backends = [OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Attachment.objects.filter(uploader=self.request.user)

    def perform_create(self, serializer):
        file_obj = self.request.data.get("file")
        if not file_obj:
            raise exceptions.ValidationError({"file": "No file provided."})

        serializer.save(
            uploader=self.request.user,
            file_name=file_obj.name,
            file_size=file_obj.size,
            mime_type=file_obj.content_type,
        )

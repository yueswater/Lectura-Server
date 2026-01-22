from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view
from rest_framework import exceptions, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from .models import EmailTemplate, Letter
from .serializers import EmailTemplateSerializer, LetterSerializer
from .tasks import send_letter_task


@extend_schema_view(tags=["Content - Email Templates"])
class EmailTemplateViewSet(viewsets.ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(tags=["Content - Letters"])
class LetterViewSet(viewsets.ModelViewSet):
    serializer_class = LetterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["project", "is_sent"]
    search_fields = ["recipient_email"]

    def get_queryset(self):
        return Letter.objects.filter(project__owner=self.request.user)

    def perform_create(self, serializer):
        project = serializer.validated_data.get("project")
        if project.owner != self.request.user:
            raise exceptions.PermissionDenied("You do not own this project.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        letter = self.get_object()
        if letter.is_sent:
            return Response({"detail": "Letter already sent."}, status=status.HTTP_400_BAD_REQUEST)

        send_letter_task.delay(letter.id)

        return Response(
            {"status": "Email queued for sending", "detail": "The task has been sent to the background worker."}
        )

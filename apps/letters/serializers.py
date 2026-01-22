from rest_framework import serializers

from .models import EmailTemplate, Letter


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = "__all__"


class LetterSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = Letter
        fields = ["id", "project", "template", "template_name", "recipient_email", "is_sent", "sent_at", "created_at"]
        read_only_fields = ["id", "is_sent", "sent_at", "created_at"]

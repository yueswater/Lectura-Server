from rest_framework import serializers

from .models import Attachment, Handout, Section


class RecursiveSectionSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class SectionSerializer(serializers.ModelSerializer):
    children = RecursiveSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = [
            "id",
            "handout",
            "title",
            "content",
            "order",
            "level",
            "children",
            "parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["level", "order", "children", "created_at", "updated_at"]
        extra_kwargs = {"content": {"allow_blank": True}}

    def validate(self, data):
        user = self.context["request"].user

        if not self.instance:
            if user.get_total_usage() >= user.storage_limit:
                raise serializers.ValidationError({"storage": "Storage limit reached. Cannot add more content."})
        else:
            new_content = data.get("content", self.instance.content)
            old_content_len = len(self.instance.content) if self.instance.content else 0
            added_size = len(new_content) - old_content_len

            if added_size > 0 and (user.get_total_usage() + added_size) > user.storage_limit:
                raise serializers.ValidationError({"storage": "Content too large. Not enough storage space remaining."})

        return data


class HandoutSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Handout
        fields = [
            "id",
            "project",
            "folder",
            "title",
            "subtitle",
            "description",
            "yaml_config",
            "is_published",
            "sections",
            "created_at",
            "updated_at",
            "file_size",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        project = data.get("project")
        folder = data.get("folder")
        if folder and folder.project != project:
            raise serializers.ValidationError(
                {"folder": "The selected folder does not belong to the selected project."}
            )

        user = self.context["request"].user
        if not self.instance and user.get_total_usage() >= user.storage_limit:
            raise serializers.ValidationError({"storage": "Storage limit reached. Cannot create handout."})

        return data


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "file", "file_url", "file_name", "caption", "alt_text", "file_size", "mime_type", "created_at"]
        read_only_fields = ["id", "file_url", "file_name", "file_size", "mime_type", "created_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def validate_file(self, value):
        user = self.context["request"].user
        if (user.get_total_usage() + value.size) > user.storage_limit:
            raise serializers.ValidationError("Uploading this file will exceed your storage limit.")
        return value

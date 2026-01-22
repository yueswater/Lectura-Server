from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Folder, Project, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color"]
        read_only_fields = ["id"]


class FolderSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["id", "name", "parent", "children", "created_at"]

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_children(self, obj):
        serializer = FolderSerializer(obj.children.all(), many=True)
        return serializer.data


class ProjectSerializer(serializers.ModelSerializer):
    root_folders = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), source="tags", write_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "description", "root_folders", "tags", "tag_ids", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    @extend_schema_field(FolderSerializer(many=True))
    def get_root_folders(self, obj):
        roots = obj.folders.filter(parent__isnull=True)
        return FolderSerializer(roots, many=True).data

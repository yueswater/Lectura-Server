from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Project, Tag


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "owner", "color")
    search_fields = ("name", "owner__username")


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ("name", "owner", "created_at")
    filter_horizontal = ("tags",)

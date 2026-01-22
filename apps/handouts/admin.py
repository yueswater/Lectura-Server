import yaml
from django.contrib import admin
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin, TabularInline

from .models import Handout, Section


class SectionInline(TabularInline):
    model = Section
    extra = 1
    fields = ("title", "order", "content")


@admin.register(Handout)
class HandoutAdmin(ModelAdmin):
    list_display = (
        "title",
        "subtitle",
        "project",
        "folder",
        "is_published",
        "updated_at",
        "display_yaml_config",
        "get_readable_file_size",
        "last_downloaded_at",
    )
    list_filter = ("is_published", "project")
    search_fields = ("title",)
    inlines = [SectionInline]
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="File size")
    def get_readable_file_size(self, obj):
        if obj.file_size:
            return filesizeformat(obj.file_size)
        return "0 Bytes"

    @admin.display(description="Yaml config")
    def display_yaml_config(self, obj):
        config = obj.yaml_config

        if isinstance(config, str):
            try:
                config = yaml.safe_load(config)
            except Exception:
                return config if config else "-"

        if not isinstance(config, dict) or not config:
            return "-"

        items_html = "".join(
            [
                format_html(
                    "<li><strong style='color: var(--primary-500);'>{}</strong>: {}</li>",
                    key,
                    value,
                )
                for key, value in config.items()
            ]
        )

        style = "list-style: none; padding: 0; margin: 0; font-size: 0.85rem; line-height: 1.4;"
        return mark_safe(f"<ul style='{style}'>{items_html}</ul>")


@admin.register(Section)
class SectionAdmin(ModelAdmin):
    list_display = ("title", "handout", "order")
    list_filter = ("handout",)
    ordering = ("handout", "order")

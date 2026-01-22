from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import EmailTemplate, Letter


@admin.register(EmailTemplate)
class EmailTemplateAdmin(ModelAdmin):
    list_display = ("name", "subject", "updated_at")
    search_fields = ("name", "subject")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Letter)
class LetterAdmin(ModelAdmin):
    list_display = ("recipient_email", "template", "is_sent", "sent_at", "created_at")
    list_filter = ("is_sent", "template")
    search_fields = ("recipient_email",)
    fields = ("template", "recipient_email", "context", "is_sent", "sent_at", "created_at")
    readonly_fields = ("sent_at", "created_at")

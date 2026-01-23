import uuid

from django.db import models
from handouts.utils import trigger_storage_email
from projects.models import Folder, Project

from .enums import SectionLevel


def attachment_upload_path(instance, filename):
    return f"attachments/user_{instance.uploader.id}/{filename}"


class Handout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="handouts")
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True, related_name="handouts")
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    file_size = models.BigIntegerField(null=True, blank=True, help_text="Size in bytes")
    last_downloaded_at = models.DateTimeField(null=True, blank=True, help_text="Last PDF generation time")
    yaml_config = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "handouts"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    handout = models.ForeignKey(Handout, on_delete=models.CASCADE, related_name="sections")

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent section (if any)",
    )
    level = models.CharField(
        max_length=20,
        choices=SectionLevel.choices,
        default=SectionLevel.SECTION,
        help_text="Hierarchy level: section (h2), subsection (h3), etc.",
    )

    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Markdown or Block JSON content", blank=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sections"
        ordering = ["order"]

    def __str__(self):
        return f"{self.handout.title} - {self.get_level_display()} - {self.title}"

    def save(self, *args, **kwargs):
        user = self.handout.project.owner
        if not self.id and user.get_total_usage() >= user.storage_limit:
            raise PermissionError("Storage limit reached. Cannot add more content.")
        if self.parent:
            if self.parent.level == SectionLevel.SECTION:
                self.level = SectionLevel.SUBSECTION
            elif self.parent.level == SectionLevel.SUBSECTION:
                self.level = SectionLevel.SUBSUBSECTION

        if not self.id and self.order == 0:
            siblings = Section.objects.filter(handout=self.handout, parent=self.parent)
            last_order = siblings.aggregate(models.Max("order"))["order__max"]
            self.order = (last_order or 0) + 1

        super().save(*args, **kwargs)

        self.update_owner_storage_status()

    def delete(self, *args, **kwargs):
        user = self.handout.project.owner
        super().delete(*args, **kwargs)

        self.update_owner_storage_status(user_instance=user)

    def update_owner_storage_status(self, user_instance=None):
        user = user_instance or self.handout.project.owner
        usage = user.get_total_usage()
        limit = user.storage_limit

        # Update the database field
        user.current_storage_usage = usage
        user.save(update_fields=["current_storage_usage"])

        usage_percentage = (usage / limit) * 100 if limit > 0 else 0

        if usage_percentage >= 90:
            trigger_storage_email(user, usage, limit, level=90)
        elif usage_percentage >= 75:
            trigger_storage_email(user, usage, limit, level=75)
        elif usage_percentage < 70:
            if user.last_storage_warning_level > 0:
                user.last_storage_warning_level = 0
                user.save(update_fields=["last_storage_warning_level"])


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploader = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_upload_path)
    file_name = models.CharField(max_length=255)

    caption = models.CharField(max_length=255, blank=True, help_text="Visible title below the image")
    alt_text = models.CharField(max_length=255, blank=True, help_text="Description for screen readers")

    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    mime_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attachments"

    def __str__(self):
        return f"{self.file_name} (Caption: {self.caption})"

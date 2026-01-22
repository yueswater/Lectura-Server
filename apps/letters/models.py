import uuid

from django.db import models

LANGUAGES = [
    ("en-us", "English"),
    ("zh-hant", "Traditional Chinese"),
    ("zh-hans", "Simplified Chinese"),
    ("th", "Thai"),
]


class EmailTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    language = models.CharField(max_length=10, choices=LANGUAGES, default="en-us")
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True, help_text="Plain text version of the email")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_templates"
        unique_together = ("name", "language")

    def __str__(self):
        return self.name


class Letter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, null=True, blank=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True)

    recipient_email = models.EmailField()
    context = models.JSONField(default=dict, blank=True)
    final_subject = models.CharField(max_length=255, blank=True)
    final_content = models.TextField(blank=True)

    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "letters"

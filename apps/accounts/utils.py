import os

from django.conf import settings
from letters.models import EmailTemplate, Letter
from letters.tasks import send_letter_task


def get_avatar_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"avatars/user_{instance.id}{ext}"


def trigger_password_reset_email(user, reset_token_obj):
    template_name = "password_reset"

    language_aliases = {
        "zh_TW": ["zh-hant", "zh-tw", "zh_TW"],
        "zh_CN": ["zh-hans", "zh-cn", "zh_CN"],
        "th": ["th"],
        "en": ["en", "en-us"],
    }

    user_lang = getattr(user, "language", "zh_TW")
    search_langs = language_aliases.get(user_lang, []) + language_aliases["zh_TW"] + language_aliases["en"]

    template = None
    for lang_code in search_langs:
        template = EmailTemplate.objects.filter(name=template_name, language=lang_code).first()
        if template:
            break

    if not template:
        return f"No template found for {template_name}"

    letter = Letter.objects.create(
        template=template,
        recipient_email=user.email,
        context={
            "username": user.username,
            "otp": reset_token_obj.otp,
            "token": str(reset_token_obj.token),
            "reset_url": f"{settings.FRONTEND_URL}/reset-password",
            "expiry_minutes": 30,
        },
    )

    send_letter_task.delay(letter.id)

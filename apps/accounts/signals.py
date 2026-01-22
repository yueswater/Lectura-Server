from django.dispatch import receiver
from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created
from letters.utils import send_templated_email


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    reset_url = "{}?token={}".format(
        instance.request.build_absolute_uri(reverse("password_reset:confirm")),
        reset_password_token.key,
    )
    context = {
        "username": reset_password_token.user.username,
        "reset_url": reset_url,
    }
    send_templated_email(
        template_name="password_reset", context_data=context, to_emails=[reset_password_token.user.email]
    )

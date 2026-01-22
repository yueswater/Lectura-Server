from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils import timezone


def send_templated_email(letter, context_data=None):
    """
    Renders a database template inside a base file-based layout and sends it.
    """
    if context_data is None:
        context_data = {"recipient_email": letter.recipient_email, "project_name": letter.project.name}

    try:
        template = letter.template

        subject = Template(template.subject).render(Context(context_data))
        inner_html = Template(template.html_content).render(Context(context_data))
        text_body = Template(template.text_content).render(Context(context_data))

        final_html_body = render_to_string("emails/base_layout.html", {"body_content": inner_html, "subject": subject})

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body if text_body else inner_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[letter.recipient_email],
        )
        msg.attach_alternative(final_html_body, "text/html")

        if msg.send():
            letter.is_sent = True
            letter.sent_at = timezone.now()
            letter.save()
            return True
        return False
    except Exception:
        return False

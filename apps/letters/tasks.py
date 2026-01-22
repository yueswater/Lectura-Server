from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.utils import timezone
from letters.models import Letter


@shared_task
def send_letter_task(letter_id):
    try:
        letter = Letter.objects.get(id=letter_id)
        template_obj = letter.template

        if not template_obj:
            return f"Failed: No template associated with letter {letter_id}"

        ctx = Context(letter.context)

        subject = Template(template_obj.subject).render(ctx)
        html_rendered = Template(template_obj.html_content).render(ctx)

        msg = EmailMultiAlternatives(
            subject=subject,
            body="Please view this email in an HTML compatible email client.",
            from_email=None,
            to=[letter.recipient_email],
        )
        msg.attach_alternative(html_rendered, "text/html")
        msg.send()

        letter.is_sent = True
        letter.sent_at = timezone.now()
        letter.final_subject = subject
        letter.final_content = html_rendered
        letter.save()

        return f"Successfully sent to {letter.recipient_email}"
    except Exception as e:
        return f"Failed: {str(e)}"

from unittest.mock import patch

import pytest
from accounts.models import User
from letters.models import EmailTemplate, Letter
from projects.models import Project
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(username="mailer@example.com", email="mailer@example.com", password="password123")


@pytest.mark.django_db
class TestLetters:
    def test_email_dispatch_flow(self, api_client, auth_user):
        api_client.force_authenticate(user=auth_user)
        project = Project.objects.create(name="Letter Proj", owner=auth_user)
        template = EmailTemplate.objects.create(name="n", subject="S", html_content="C")
        letter = Letter.objects.create(project=project, template=template, recipient_email="c@ex.com")

        # Consistent path based on config/urls.py
        url = f"/api/content/letters/{letter.id}/send/"

        with patch("django.core.mail.EmailMultiAlternatives.send", return_value=1):
            response = api_client.post(url)
            assert response.status_code == status.HTTP_200_OK

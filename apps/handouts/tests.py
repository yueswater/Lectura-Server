import pytest
from accounts.models import User
from django.urls import reverse
from handouts.models import Handout
from projects.models import Project
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user(db):
    # Fix the missing username argument
    return User.objects.create_user(username="editor@example.com", email="editor@example.com", password="password123")


@pytest.mark.django_db
class TestHandouts:
    def test_handout_pdf_generation_endpoint(self, api_client, auth_user):
        api_client.force_authenticate(user=auth_user)
        project = Project.objects.create(name="Handout Project", owner=auth_user)
        handout = Handout.objects.create(project=project, title="Test")

        # Correct path based on config: path("api/content/", include("handouts.urls"))
        try:
            url = reverse("handout-export-pdf", kwargs={"pk": handout.id})
        except Exception:
            url = f"/api/content/handouts/{handout.id}/export-pdf/"

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

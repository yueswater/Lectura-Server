import pytest
from accounts.models import User
from django.urls import reverse
from projects.models import Project
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    # Added username to fix TypeError
    return User.objects.create_user(username="owner@example.com", email="owner@example.com", password="password123")


@pytest.mark.django_db
class TestProjects:
    def test_create_project(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        url = reverse("project-list")
        data = {"name": "Alpha Project"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_project_list_security(self, api_client, test_user):
        other_user = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="password123"
        )
        Project.objects.create(name="Private Project", owner=other_user)

        api_client.force_authenticate(user=test_user)
        url = reverse("project-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

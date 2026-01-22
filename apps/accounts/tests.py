import pytest
from accounts.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestAccounts:
    def test_user_registration(self, api_client):
        url = reverse("auth_register")
        data = {"username": "testuser_reg", "email": "testuser_reg@example.com", "password": "strong_password123"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="testuser_reg@example.com").exists()

    def test_user_login_and_jwt(self, api_client):
        email = "login_test@example.com"
        password = "password123"
        User.objects.create_user(username=email, email=email, password=password)

        url = reverse("token_obtain_pair")
        data = {"username": email, "password": password}
        response = api_client.post(url, data)

        if response.status_code == 400:
            data = {"email": email, "password": password}
            response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

import pytest
from django.test import Client
from django.urls import reverse

from tests.factories.tourist import TouristProfileFactory


@pytest.mark.django_db
@pytest.mark.integration
class TestSwitchProfileView:
    def test_redirect_to_referer_when_safe(self):
        profile = TouristProfileFactory()
        client = Client()
        client.force_login(profile.user)

        url = reverse("switch_profile", kwargs={"profile_id": profile.id})
        response = client.get(url, HTTP_REFERER="http://testserver/dashboard/")

        assert response.status_code in (302, 303)
        assert response["Location"] == "http://testserver/dashboard/"

    def test_redirect_to_home_when_referer_is_external(self):
        profile = TouristProfileFactory()
        client = Client()
        client.force_login(profile.user)

        url = reverse("switch_profile", kwargs={"profile_id": profile.id})
        response = client.get(url, HTTP_REFERER="http://evil.com/phish")

        assert response.status_code in (302, 303)
        assert response["Location"] == "/"

    def test_redirect_to_home_when_no_referer(self):
        profile = TouristProfileFactory()
        client = Client()
        client.force_login(profile.user)

        url = reverse("switch_profile", kwargs={"profile_id": profile.id})
        response = client.get(url)

        assert response.status_code in (302, 303)
        assert response["Location"] == "/"

    def test_no_redirect_to_foreign_url(self):
        profile = TouristProfileFactory()
        client = Client()
        client.force_login(profile.user)

        url = reverse("switch_profile", kwargs={"profile_id": profile.id})
        malicious_referer = "https://attacker.example.com/callback"
        response = client.get(url, HTTP_REFERER=malicious_referer)

        assert response.status_code in (302, 303)
        assert response["Location"] in ("/", reverse("home"))

    def test_creates_session_active_profile(self):
        profile = TouristProfileFactory()
        client = Client()
        client.force_login(profile.user)

        url = reverse("switch_profile", kwargs={"profile_id": profile.id})
        client.get(url)

        assert client.session["active_profile_id"] == profile.id

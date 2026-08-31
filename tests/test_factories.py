import pytest
from django.contrib.auth import get_user_model

from apps.tourists.models import TouristProfile
from tests.factories.tourist import TouristProfileFactory, UserFactory


User = get_user_model()


@pytest.mark.django_db
@pytest.mark.integration
class TestUserFactory:
    def test_creates_user_with_unique_username(self):
        user = UserFactory()

        assert user.username.startswith("user")
        assert user.email.endswith("@example.com")
        assert user.check_password("changeme123")

    def test_generates_unique_usernames(self):
        u1 = UserFactory()
        u2 = UserFactory()

        assert u1.username != u2.username


@pytest.mark.django_db
@pytest.mark.integration
class TestTouristProfileFactory:
    def test_creates_profile_linked_to_user(self):
        profile = TouristProfileFactory()

        assert profile.user_id is not None
        assert profile.user.check_password("changeme123")
        assert profile.is_main_profile is True

    def test_generates_unique_nicknames(self):
        p1 = TouristProfileFactory()
        p2 = TouristProfileFactory()

        assert p1.nickname != p2.nickname

    def test_respects_unique_together_constraint(self):
        profile = TouristProfileFactory()

        assert TouristProfile.objects.filter(user=profile.user, nickname=profile.nickname).exists()

    def test_profile_is_touristprofile_instance(self):
        profile = TouristProfileFactory()

        assert isinstance(profile, TouristProfile)

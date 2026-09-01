import factory
from django.contrib.auth import get_user_model
from factory import django

from apps.tourists.models import TouristProfile

User = get_user_model()


class UserFactory(django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name", locale="pl_PL")
    last_name = factory.Faker("last_name", locale="pl_PL")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if create:
            self.set_password("changeme123")
            self.save()


class TouristProfileFactory(django.DjangoModelFactory):
    class Meta:
        model = TouristProfile
        skip_postgeneration_save = True

    user = factory.SubFactory(UserFactory)
    is_main_profile = True
    nickname = factory.Sequence(lambda n: f"turista{n}")
    birth_date = factory.Faker("date_of_birth", minimum_age=18, maximum_age=65)
    preferred_base_map = "carto"
    club_join_dates = factory.LazyFunction(lambda: {"KGP": "2020-01-01"})
    active_plan = "FREE"
    max_photos_per_ascent = 3
    max_active_badges = 3

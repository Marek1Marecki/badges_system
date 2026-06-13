"""Sygnały dla obszaru Turysty.

Automatyzuje procesy integracyjne na styku frameworka Django (auth)
a naszą Czystą Domeną i profilami.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tourists.models import TouristProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_tourist_profile(sender, instance, created, **kwargs) -> None:
    """Automatycznie tworzy TouristProfile po pierwszym logowaniu przez Google OAuth."""
    if created:
        # Generujemy tymczasowy nickname na bazie e-maila
        base_nickname = instance.email.split("@")[0] if instance.email else f"user_{instance.id}"
        nickname = f"{base_nickname}_{instance.id}"

        # Domyślny przydział zasobów z US-C01c (Freemium)
        TouristProfile.objects.create(
            user=instance,
            nickname=nickname,
            active_plan="FREE",
            max_photos_per_ascent=1,
            max_active_badges=3,
        )

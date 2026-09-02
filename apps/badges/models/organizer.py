"""Model organizatora odznak."""

from django.db import models


class OrganizerModel(models.Model):
    """Reprezentuje organizatora odznaki (np.

    Oddział PTTK, Klub).
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Nazwa organizatora",
    )
    contact_info = models.TextField(
        blank=True,
        verbose_name="Dane kontaktowe",
    )
    club_rules_link = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Regulamin klubu (Link)",
    )
    # Pliki wizualne (Opcjonalne)
    club_badge_image = models.ImageField(
        upload_to="organizers/badges/",
        blank=True,
        null=True,
        verbose_name="Odznaka klubowa",
    )
    is_booklet_required = models.BooleanField(
        default=False,
        verbose_name="Wymagana książeczka klubowa",
        help_text=(
            "Zaznacz, jeśli organizator bezwzględnie wymaga posiadania swojej książeczki do zdobywania jego odznak."
        ),
    )
    booklet_template_pdf = models.FileField(
        upload_to="organizers/booklets/",
        blank=True,
        null=True,
        verbose_name="Wzór książeczki (PDF)",
    )
    has_publication_consent = models.BooleanField(
        default=False,
        verbose_name="Zgoda na publikację",
        help_text=(
            "Zaznacz, jeśli masz zgodę organizatora na publikację wizerunku odznak, książeczek i treści regulaminów."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Konfiguracja modelu OrganizerModel."""

        db_table = "odznaki_organizer"
        verbose_name = "Organizator"
        verbose_name_plural = "Organizatorzy"
        ordering = ["name"]

    def __str__(self) -> str:
        """Reprezentacja tekstowa organizatora."""
        return str(self.name)

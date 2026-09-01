"""Modele danych dla obszaru Turysty (B2C) - Model Rodzinny.

Odizolowane od słowników PTTK (apps/badges/).
Zarządzają kontami, profilami (dzieci/rodzice), logami wejść i postępami.
"""

from django.conf import settings
from django.db import models  # <--- TEGO ZABRAKŁO!

from apps.badges.models import BadgeModel, BadgeVersionModel, TouristObject


def profile_directory_path(instance, filename: str) -> str:
    """Dynamicznie generuje ścieżkę do zdjęcia: media/ascents/profile_<id>/<data>_<plik>.

    Args:
      instance:
      filename: str:
      filename: str:

    Returns:
    """
    return f"ascents/profile_{instance.profile_id}/{instance.ascent_date}_{filename}"


class TouristProfile(models.Model):
    """Profil Turysty.

    Jedno konto User może posiadać wiele profili (Konto Rodzinne).
    """

    # ZMIANA: ForeignKey zamiast OneToOne!
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profiles")
    is_main_profile = models.BooleanField(default=False, verbose_name="Główny profil konta")

    nickname = models.CharField(max_length=100, verbose_name="Pseudonim (Publiczny)")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Data urodzenia")
    preferred_base_map = models.CharField(max_length=20, default="carto", verbose_name="Preferowany podkład mapy")

    # Słownik klubów (np. "KGP": "2020-01-01")
    club_join_dates = models.JSONField(default=dict, blank=True, verbose_name="Przynależność klubowa")

    # System Freemium (Quotas) - Zwykle egzekwowane na głównym profilu
    active_plan = models.CharField(max_length=50, default="FREE", verbose_name="Aktywny pakiet")
    max_photos_per_ascent = models.IntegerField(default=1, verbose_name="Limit zdjęć per log")
    max_active_badges = models.IntegerField(default=3, verbose_name="Limit aktywnych odznak")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Konfiguracja modelu TouristProfile."""

        db_table = "tourists_profile"
        verbose_name = "Profil Turysty"
        verbose_name_plural = "Profile Turystów"
        # Użytkownik nie może mieć w rodzinie dwóch profili o tej samej nazwie
        unique_together = ("user", "nickname")

    def __str__(self) -> str:
        """Reprezentacja tekstowa profilu turystycznego."""
        marker = " [GŁÓWNY]" if self.is_main_profile else ""
        return f"{self.nickname} ({self.user.email}){marker}"


class AscentLog(models.Model):
    """Historyczny dziennik wejść.

    Czysta ewidencja faktów.
    """

    # ZMIANA: Wskazuje na Profil, a nie na Usera!
    # AUDYT-045: PROTECT chroni wejścia przed utratą przy usunięciu profilu.
    profile = models.ForeignKey(TouristProfile, on_delete=models.PROTECT, related_name="ascents")
    peak = models.ForeignKey(TouristObject, on_delete=models.PROTECT, related_name="ascents_logged")
    ascent_date = models.DateField(verbose_name="Data wejścia")

    souvenir_image = models.ImageField(
        upload_to=profile_directory_path,
        null=True,
        blank=True,
        verbose_name="Zdjęcie pamiątkowe",
        help_text=(
            "Ochrona: Django ImageField weryfikuje nagłówek obrazu (Pillow). "
            "BRAK: limit rozmiaru (DoS) oraz wyraźna walidacja MIME — zob. AUDYT-028. "
            "Upload przez API nie jest jeszcze obsługiwany (tylko Admin); "
            "przed dodaniem endpointu REST trzeba dodać validator rozmiaru + Content-Type."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Konfiguracja modelu AscentLog."""

        db_table = "tourists_ascent_log"
        verbose_name = "Log Wejścia"
        verbose_name_plural = "Logi Wejść"
        # ZMIANA: Zabezpieczenie upsert chroni teraz Profil, a nie Usera
        constraints = [
            models.UniqueConstraint(fields=["profile", "peak", "ascent_date"], name="unique_ascent_per_day_per_profile")
        ]
        # AUDYT-029: indeks złożony na (profile_id, ascent_date) dla get_oldest_ascent_date
        indexes = [
            models.Index(fields=["profile", "ascent_date"], name="ascent_profile_date_idx"),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa zdarzenia wejścia na szczyt."""
        return f"{self.profile.nickname} - {self.peak.name} ({self.ascent_date})"


class DomainStatus(models.TextChoices):
    """Status domeny obiektu turystycznego."""

    NOT_STARTED = "NOT_STARTED", "Subskrybowana (Czeka na logi)"
    IN_PROGRESS = "IN_PROGRESS", "W trakcie zdobywania"
    COMPLETED = "COMPLETED", "Skompletowana matematycznie"


class LogisticStatus(models.TextChoices):
    """Status logistyczny obiektu turystycznego."""

    WAITING_FOR_SEND = "WAITING_FOR_SEND", "Gotowa do wysyłki (Skompletowana)"
    WAITING_FOR_VERIFICATION = "WAITING_FOR_VERIFICATION", "Wysłana do PTTK (Weryfikacja)"
    WAITING_FOR_RECEIVING = "WAITING_FOR_RECEIVING", "Zatwierdzona (Czeka na listonosza)"
    ALBUM = "ALBUM", "Wpięta do albumu (Zakończone)"


class UserBadgeProgress(models.Model):
    """Zmaterializowany stan zdobywania odznaki (Subskrypcja + Snapshot)."""

    # ZMIANA: Wskazuje na Profil, a nie na Usera!
    # AUDYT-045: PROTECT chroni postępy przed utratą przy usunięciu profilu.
    profile = models.ForeignKey(TouristProfile, on_delete=models.PROTECT, related_name="badge_progresses")
    badge = models.ForeignKey(BadgeModel, on_delete=models.CASCADE, related_name="user_progresses")
    version = models.ForeignKey(
        BadgeVersionModel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="anchored_users",
        help_text="Zabetonowana wersja regulaminu po pierwszym zgłoszonym wejściu.",
    )

    cycle_number = models.IntegerField(default=1, verbose_name="Cykl / Edycja")

    domain_status = models.CharField(max_length=20, choices=DomainStatus.choices, default=DomainStatus.NOT_STARTED)
    logistic_status = models.CharField(max_length=30, choices=LogisticStatus.choices, null=True, blank=True)
    logistic_status_date = models.DateField(null=True, blank=True, verbose_name="Data zmiany logistyki")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Konfiguracja modelu UserBadgeProgress."""

        db_table = "tourists_badge_progress"
        verbose_name = "Postęp Odznaki (Subskrypcja)"
        verbose_name_plural = "Postępy Odznak"
        # ZMIANA: Zabezpieczenie przed dublowaniem cykli u jednego Profilu
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "badge", "cycle_number"], name="unique_active_cycle_per_badge_per_profile"
            )
        ]
        # AUDYT-029: composite index dla zapytań Czystej Domeny o postęp
        indexes = [
            models.Index(fields=["profile", "badge", "domain_status"], name="progress_p_b_s_idx"),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa postępu użytkownika w odznadze."""
        ver = self.version.version_code if self.version else "BRAK (Oczekuje)"
        return f"{self.profile.nickname} | {self.badge.code} [{ver}] (Cykl {self.cycle_number}) | {self.domain_status}"

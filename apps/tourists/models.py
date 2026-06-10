"""Modele danych dla obszaru Turysty (B2C).

Odizolowane od słowników PTTK (apps/badges/).
Zarządzają profilami, logami wejść oraz postępami w zdobywaniu odznak.
"""

from django.conf import settings
from django.db import models

# Importujemy modele z aplikacji słownikowej
from apps.badges.models import BadgeModel, BadgeVersionModel, TouristObject


def user_directory_path(instance, filename: str) -> str:
    """Dynamicznie generuje ścieżkę do zdjęcia: media/ascents/user_<id>/<data>_<plik>."""
    return f"ascents/user_{instance.user_id}/{instance.ascent_date}_{filename}"


class TouristProfile(models.Model):
    """Rozszerzenie standardowego modelu User o dane domenowe i limity Freemium."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tourist_profile")
    nickname = models.CharField(max_length=100, unique=True, verbose_name="Pseudonim (Publiczny)")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Data urodzenia")

    # Słownik klubów (np. "KGP": "2020-01-01")
    club_join_dates = models.JSONField(default=dict, blank=True, verbose_name="Przynależność klubowa")

    # System Freemium (Quotas)
    active_plan = models.CharField(max_length=50, default="FREE", verbose_name="Aktywny pakiet")
    max_photos_per_ascent = models.IntegerField(default=1, verbose_name="Limit zdjęć per log")
    max_active_badges = models.IntegerField(default=3, verbose_name="Limit aktywnych odznak")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tourists_profile"
        verbose_name = "Profil Turysty"
        verbose_name_plural = "Profile Turystów"

    def __str__(self) -> str:
        return f"{self.nickname} ({self.user.email})"


class AscentLog(models.Model):
    """Historyczny dziennik wejść. Czysta ewidencja faktów."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ascents")
    peak = models.ForeignKey(TouristObject, on_delete=models.PROTECT, related_name="ascents_logged")
    ascent_date = models.DateField(verbose_name="Data wejścia")

    # Opcjonalna pamiątka, katalogowana per użytkownik!
    souvenir_image = models.ImageField(
        upload_to=user_directory_path, null=True, blank=True, verbose_name="Zdjęcie pamiątkowe"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tourists_ascent_log"
        verbose_name = "Log Wejścia"
        verbose_name_plural = "Logi Wejść"
        # Invariant D-04: Blokada duplikatów (Upsert Guard)
        constraints = [models.UniqueConstraint(fields=["user", "peak", "ascent_date"], name="unique_ascent_per_day")]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.peak.name} ({self.ascent_date})"


class DomainStatus(models.TextChoices):
    """Statusy matematyczne wyliczane przez Czystą Domenę."""

    NOT_STARTED = "NOT_STARTED", "Subskrybowana (Czeka na logi)"
    IN_PROGRESS = "IN_PROGRESS", "W trakcie zdobywania"
    COMPLETED = "COMPLETED", "Skompletowana matematycznie"


class LogisticStatus(models.TextChoices):
    """Statusy Osobistego Trackera Turysty (Maszyna Stanów Kanban)."""

    WAITING_FOR_SEND = "WAITING_FOR_SEND", "Gotowa do wysyłki (Skompletowana)"
    WAITING_FOR_VERIFICATION = "WAITING_FOR_VERIFICATION", "Wysłana do PTTK (Weryfikacja)"
    WAITING_FOR_RECEIVING = "WAITING_FOR_RECEIVING", "Zatwierdzona (Czeka na listonosza)"
    ALBUM = "ALBUM", "Wpięta do albumu (Zakończone)"


class UserBadgeProgress(models.Model):
    """Zmaterializowany stan zdobywania odznaki (Subskrypcja + Snapshot)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badge_progresses")
    # Twarde przypięcie intencji (Jaką odznakę chcę zdobywać?)
    badge = models.ForeignKey(BadgeModel, on_delete=models.CASCADE, related_name="user_progresses")
    # Leniwe zakotwiczenie Praw Nabytych (US-C05) - na początku PUSTE!
    version = models.ForeignKey(
        BadgeVersionModel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="anchored_users",
        help_text="Zabetonowana wersja regulaminu po pierwszym zgłoszonym wejściu.",
    )

    cycle_number = models.IntegerField(default=1, verbose_name="Cykl / Edycja")

    # Stany
    domain_status = models.CharField(max_length=20, choices=DomainStatus.choices, default=DomainStatus.NOT_STARTED)
    logistic_status = models.CharField(max_length=30, choices=LogisticStatus.choices, null=True, blank=True)
    logistic_status_date = models.DateField(null=True, blank=True, verbose_name="Data zmiany logistyki")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tourists_badge_progress"
        verbose_name = "Postęp Odznaki (Subskrypcja)"
        verbose_name_plural = "Postępy Odznak"
        # Turysta może mieć tylko jeden aktywny wpis dla danej odznaki w danym cyklu
        constraints = [
            models.UniqueConstraint(fields=["user", "badge", "cycle_number"], name="unique_active_cycle_per_badge")
        ]

    def __str__(self) -> str:
        ver = self.version.version_code if self.version else "BRAK (Oczekuje)"
        return f"{self.user.email} | {self.badge.code} [{ver}] (Cykl {self.cycle_number}) | {self.domain_status}"

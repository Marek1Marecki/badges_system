"""Agregat domenowy Profilu Turysty.

AUDYT-037: enkapsuluje reguły biznesowe (limity Freemium) i ochronione
mutacje profilu, które dotychczas były rozsiane po Use Case'ach.

Agregat jest niezależny od Django ORM i od `TouristProfileDTO` (transportu).
Może być hydratowany z repozytorium (lub z DTO) i odgrywany z powrotem.
Emitowane zdarzenia `ProfileUpdated` stanowią podstawę audit trailu (AUDYT-051).
"""

from dataclasses import dataclass, field

from domain.events import DomainEvent, ProfileUpdated


@dataclass(frozen=True)
class TouristProfileDomain:
    """Czysty agregat domenowy profilu turysty (Konto Rodzinne).

    Trzyma jedynie niezbędne dane + limity Freemium. Logika walidacji
    limitów jest scentralizowana tutaj — Use Case'y mogą jedynie pytać
    `can_log_ascent(...)` / `can_track_new_badge(...)` zamiast kopiować
    te same operacje.

    Pola:
        profile_id           — klucz główny profilu
        is_main_profile      — Czy profil jest głównym profilem (na nim obowiązują limity)
        club_join_dates      — Słownik kod klubu -> data dołączenia
        active_plan          — Aktywny pakiet (np. "FREE", "PRO")
        max_photos_per_ascent— Limit zdjęć na jedno wejście
        max_active_badges    — Limit jednocześnie aktywnych odznak
        pending_events       — Wewnętrzna kolejka emitowanych zdarzeń
    """

    profile_id: int
    is_main_profile: bool
    active_plan: str
    max_photos_per_ascent: int
    max_active_badges: int
    club_join_dates: dict[str, str] = field(default_factory=dict)
    pending_events: list[DomainEvent] = field(default_factory=list, repr=False)

    # --------------------------------------------------------------------------- #
    # Freemium — czytane limity
    # --------------------------------------------------------------------------- #
    def can_log_ascent(self, photo_count: int) -> bool:
        """Sprawdza, czy turysta może zalogować wejście z `photo_count` zdjęciami.

        Zasada: jeżeli limity nie obowiązują (np. profil nie-główny), przyjmujemy
        liberalny dostęp — limity są egzekwowane wyłącznie na profilu głównym.
        """
        if not self.is_main_profile:
            return True
        return photo_count <= self.max_photos_per_ascent

    def can_track_new_badge(self, current_active_count: int) -> bool:
        """Sprawdza, czy turysta może rozpocząć śledzenie kolejnej odznaki.

        Argument `current_active_count` = liczba już aktywnych odznak turysty.
        """
        if not self.is_main_profile:
            return True
        return current_active_count < self.max_active_badges

    # --------------------------------------------------------------------------- #
    # Mutacje (zawsze zwracają nową instancję — immutable aggregate)
    # --------------------------------------------------------------------------- #
    def with_nickname(self, new_nickname: str, actor_user_id: int) -> "TouristProfileDomain":
        """Zmienia pseudonim, emitując zdarzenie `ProfileUpdated`.

        Invariant: nickname nie może być pusty → `ValueError`.
        """
        if not new_nickname or not new_nickname.strip():
            raise ValueError("Pseudonim profilu nie może być pusty.")

        event = ProfileUpdated(
            actor_user_id=actor_user_id,
            target_profile_id=self.profile_id,
            changed_fields=("nickname",),
        )
        return TouristProfileDomain(
            profile_id=self.profile_id,
            is_main_profile=self.is_main_profile,
            active_plan=self.active_plan,
            max_photos_per_ascent=self.max_photos_per_ascent,
            max_active_badges=self.max_active_badges,
            club_join_dates=dict(self.club_join_dates),
            pending_events=self._append_event(event),
        )

    def with_upgraded_plan(
        self,
        plan: str,
        max_photos: int,
        max_badges: int,
        actor_user_id: int,
    ) -> "TouristProfileDomain":
        """Awansuje profil na wyższy pakiet Freemium."""
        changed_fields = tuple(
            label
            for label, old, new in (
                ("active_plan", self.active_plan, plan),
                ("max_photos_per_ascent", self.max_photos_per_ascent, max_photos),
                ("max_active_badges", self.max_active_badges, max_badges),
            )
            if old != new
        )

        event = ProfileUpdated(
            actor_user_id=actor_user_id,
            target_profile_id=self.profile_id,
            changed_fields=changed_fields,
        )
        return TouristProfileDomain(
            profile_id=self.profile_id,
            is_main_profile=self.is_main_profile,
            active_plan=plan,
            max_photos_per_ascent=max_photos,
            max_active_badges=max_badges,
            club_join_dates=dict(self.club_join_dates),
            pending_events=self._append_event(event),
        )

    def events(self) -> tuple[DomainEvent, ...]:
        """Zwraca akumulowane zdarzenia (do odczytania przez Use Case / Adaptery)."""
        return tuple(self.pending_events)

    # --------------------------------------------------------------------------- #
    # wewnętrzne
    # --------------------------------------------------------------------------- #
    def _append_event(self, event: DomainEvent) -> list[DomainEvent]:
        return [*self.pending_events, event]

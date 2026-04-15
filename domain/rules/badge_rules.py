"""Reguły biznesowe zdobywania odznak (Wzorzec Strategii)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from domain.value_objects.ascent import ActivityType, Ascent


class BadgeRule(ABC):
    """Bazowy interfejs dla wszystkich reguł."""

    @abstractmethod
    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Zwraca listę błędów. Pusta lista oznacza spełnienie reguły.

        Args:
            ascents: Lista wejść na szczyty.

        Returns:
            Lista błędów w postaci ciągów znaków.
        """


@dataclass(frozen=True)
class ActivityRule(BadgeRule):
    """Reguła ograniczająca typ dozwolonych aktywności."""

    allowed_activities: set[ActivityType]

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza, czy wszystkie wejścia mają dozwoloną aktywność.

        Args:
            ascents: Lista wejść do sprawdzenia.

        Returns:
            Lista komunikatów o błędach.
        """
        errors = []
        for ascent in ascents:
            if ascent.activity not in self.allowed_activities:
                errors.append(f"Aktywność {ascent.activity.value} jest niedozwolona.")
        return errors


@dataclass(frozen=True)
class TimeLimitRule(BadgeRule):
    """Reguła określająca limit czasu na ukończenie zdobywania."""

    limit_in_years: int

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza czas między pierwszym a ostatnim wejściem.

        Args:
            ascents: Lista wejść do sprawdzenia.

        Returns:
            Lista komunikatów o błędach w przypadku przekroczenia czasu.
        """
        if not ascents:
            return []

        first_ascent = min(ascents, key=lambda a: a.ascent_date)
        last_ascent = max(ascents, key=lambda a: a.ascent_date)

        limit_days = self.limit_in_years * 365
        delta = (last_ascent.ascent_date - first_ascent.ascent_date).days

        if delta > limit_days:
            return [f"Przekroczono limit {self.limit_in_years} lat (trwało {delta} dni)."]

        return []


@dataclass(frozen=True)
class RequiresClubJoinDateRule(BadgeRule):
    """Reguła wymagająca przynależności do klubu (np. Klub Zdobywców KGP).

    Tylko wejścia (Ascents) zarejestrowane PO dacie dołączenia turysty do
    klubu mogą być zaliczone na poczet tej odznaki.
    """

    # Ta reguła jest po prostu "flagą" włączaną w panelu Admina.
    # W przyszłości (Faza C) metoda validate() przyjmie dodatkowy parametr:
    # `context: VerificationContext`, z którego wyciągniemy prawdziwą datę.

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza, czy wejścia są późniejsze niż data dołączenia do klubu.

        Args:
            ascents: Lista wejść do sprawdzenia.

        Returns:
            Lista komunikatów o błędach dla wejść sprzed daty dołączenia.
        """
        errors = []

        # TODO: Faza C - Usunąć ten hardcode! Zastąpić pobraniem daty z kontekstu Turysty.
        # Tymczasowe założenie do testów: "Turysta zapisał się do klubu 1 stycznia 2020 r."
        mock_club_join_date = date(2020, 1, 1)

        for ascent in ascents:
            if ascent.ascent_date < mock_club_join_date:
                errors.append(
                    f"Wejście na szczyt (ID: {ascent.peak_id}) odrzucone. "
                    f"Data wejścia ({ascent.ascent_date}) jest przed datą dołączenia do klubu ({mock_club_join_date})."
                )

        return errors

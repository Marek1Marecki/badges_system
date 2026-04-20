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


@dataclass(frozen=True)
class MinAgeRule(BadgeRule):
    """Reguła minimalnego wieku wymagana do zdobywania odznaki.

    Weryfikuje, czy turysta w dniu wejścia na szczyt miał ukończony
    określony wiek (np. 8 lat).
    """

    min_age: int

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza, czy wiek w dniu wejścia spełnia minimalny próg.

        Args:
            ascents: Lista wejść do sprawdzenia.

        Returns:
            Lista komunikatów o błędach dla wejść poniżej wymaganego wieku.
        """
        errors = []

        # TODO: Faza C - Pobrać z VerificationContext!
        # Tymczasowa zaślepka: Zakładamy, że turysta urodził się 1 stycznia 2015 r.
        mock_birth_date = date(2015, 1, 1)

        for ascent in ascents:
            # Precyzyjne wyliczenie wieku w dniu wejścia na szczyt (uwzględnia miesiące i dni)
            age_at_ascent = (
                ascent.ascent_date.year
                - mock_birth_date.year
                - ((ascent.ascent_date.month, ascent.ascent_date.day) < (mock_birth_date.month, mock_birth_date.day))
            )

            if age_at_ascent < self.min_age:
                errors.append(
                    f"Wejście na szczyt (ID: {ascent.peak_id}) odrzucone. "
                    f"Wiek w dniu wejścia ({age_at_ascent} lat) był mniejszy "
                    f"niż wymagane {self.min_age} lat."
                )

        return errors


@dataclass(frozen=True)
class StartDateRule(BadgeRule):
    """Reguła określająca datę, od której zaliczane są wejścia na szczyty.

    Weryfikuje, czy turysta zdobył szczyt po dacie wejścia w życie regulaminu.
    """

    start_date: date

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza, czy wejścia są późniejsze niż data wejścia regulaminu.

        Args:
            ascents: Lista wejść do sprawdzenia.

        Returns:
            Lista komunikatów o błędach dla wejść sprzed daty startowej.
        """
        errors = []
        for ascent in ascents:
            if ascent.ascent_date < self.start_date:
                errors.append(
                    f"Wejście na szczyt (ID: {ascent.peak_id}) odrzucone. "
                    f"Data wejścia ({ascent.ascent_date}) jest przed datą wejścia "
                    f"w życie regulaminu odznaki ({self.start_date})."
                )
        return errors


@dataclass(frozen=True)
class MandatoryObjectsRule(BadgeRule):
    """Reguła wymagająca zdobycia konkretnych, wskazanych obiektów z puli.

    Niezależnie od ogólnej liczby wymaganych szczytów (np. 40 dowolnych),
    te konkretne obiekty muszą zostać zdobyte, aby odznaka została zaliczona.
    """

    mandatory_peak_ids: set[int]

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza, czy turysta zdobył wszystkie obowiązkowe obiekty.

        Args:
            ascents: Lista wszystkich wejść turysty.

        Returns:
            Lista komunikatów o brakujących obowiązkowych szczytach lub pusta lista.
        """
        # Zbieramy ID wszystkich szczytów zdobytych przez turystę
        climbed_peak_ids = {ascent.peak_id for ascent in ascents}

        # Wyliczamy różnicę zbiorów: Obowiązkowe MINUS Zdobyte
        missing_mandatory_peaks = self.mandatory_peak_ids - climbed_peak_ids

        if missing_mandatory_peaks:
            # Poprawka Ruff C414: sorted() samo przyjmuje zbiory (sets)
            missing_list = sorted(missing_mandatory_peaks)
            return [f"Brakuje obowiązkowych obiektów. Musisz zdobyć obiekty o ID: {missing_list}"]

        return []


@dataclass(frozen=True)
class GroupedAlternativesRule(BadgeRule):
    """Zasada 'Wiaderek' dla odznak wymagających zdobycia obiektów z wielu grup.

    Na przykład: Odznaka wymaga wejścia na po 1 punkcie widokowym w 30
    z 38 dostępnych pasm górskich.
    Każde pasmo to jedno 'wiaderko' (zbiór IDków).
    """

    # Lista wiaderek (każde wiaderko to zbiór int)
    groups: list[set[int]]

    # Ile wiaderek (grup) trzeba zaliczyć (z każdego min. 1 obiekt)
    min_groups_required: int

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Zlicza, ile grup (wiaderek) zawiera przynajmniej jedno zdobyte wejście."""
        climbed_peak_ids = {ascent.peak_id for ascent in ascents}

        groups_completed = 0

        # Sprawdzamy każde wiaderko:
        for group in self.groups:
            # Przecięcie zbiorów (intersection). Jeśli nie jest puste,
            # to znaczy, że w tym wiaderku zdobyliśmy chociaż 1 szczyt!
            if group.intersection(climbed_peak_ids):
                groups_completed += 1

        if groups_completed < self.min_groups_required:
            return [
                f"Zbyt mało zdobytych grup (pasm). Wymagano {self.min_groups_required}, "
                f"zdobyto obiekty zaledwie z {groups_completed} grup."
            ]

        return []

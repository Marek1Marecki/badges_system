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

    @staticmethod
    def _format_rejection(ascent: Ascent, reason: str) -> str:
        """Helper ujednolicający komunikaty o odrzuceniu konkretnego wejścia."""
        return f"Wejście na obiekt (ID: {ascent.peak_id}, Data: {ascent.ascent_date}) odrzucone: {reason}."


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
                errors.append(self._format_rejection(ascent, f"Aktywność {ascent.activity.value} jest niedozwolona"))
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

        # Dodajemy lata, obsługując wyjątek z 29 lutego.
        start_date = first_ascent.ascent_date
        try:
            deadline = start_date.replace(year=start_date.year + self.limit_in_years)
        except ValueError:
            # Ten błąd wystąpi TYLKO wtedy, gdy pierwsza wycieczka była 29 lutego w roku przestępnym,
            # a rok końcowy nie jest przestępny. Przesuwamy deadline bezpiecznie na 28 lutego.
            deadline = start_date.replace(year=start_date.year + self.limit_in_years, month=2, day=28)

        if last_ascent.ascent_date > deadline:
            return [
                f"Przekroczono limit czasu. Odznaka rozpoczęta {first_ascent.ascent_date}, "
                f"wymagała ukończenia do {deadline}, a ostatnie wejście to {last_ascent.ascent_date}."
            ]

        return []


@dataclass(frozen=True)
class RequiresClubJoinDateRule(BadgeRule):
    """Reguła wymagająca przynależności do klubu (np. Klub Zdobywców KGP).

    Tylko wejścia (Ascents) zarejestrowane PO dacie dołączenia turysty do
    klubu mogą być zaliczone na poczet tej odznaki.
    """

    # TODO: Faza C - Gdy pojawi się model Turysty, usuniemy ten domyślny parametr
    # i wymusimy jego podawanie w momencie wywoływania reguły przez UseCase.
    club_join_date: date = date(2020, 1, 1)

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza, czy wejścia są późniejsze niż data dołączenia do klubu.

        Args:
            ascents: Lista wejść do sprawdzenia.

        Returns:
            Lista komunikatów o błędach dla wejść sprzed daty dołączenia.
        """
        errors = []
        for ascent in ascents:
            if ascent.ascent_date < self.club_join_date:
                errors.append(
                    self._format_rejection(
                        ascent, f"wejście odbyło się przed dołączeniem do klubu ({self.club_join_date})"
                    )
                )
        return errors


@dataclass(frozen=True)
class MinAgeRule(BadgeRule):
    """Reguła minimalnego wieku wymagana do zdobywania odznaki.

    Weryfikuje, czy turysta w dniu wejścia na szczyt miał ukończony
    określony wiek (np. 8 lat).
    """

    min_age: int
    # TODO: Faza C - Zastąpić wstrzykiwaniem daty z kontekstu prawdziwego Turysty.
    birth_date: date = date(2015, 1, 1)

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Sprawdza, czy wiek w dniu wejścia spełnia minimalny próg.

        Args:
            ascents: Lista wejść do sprawdzenia.

        Returns:
            Lista komunikatów o błędach dla wejść poniżej wymaganego wieku.
        """
        errors = []
        for ascent in ascents:
            age_at_ascent = (
                ascent.ascent_date.year
                - self.birth_date.year
                - ((ascent.ascent_date.month, ascent.ascent_date.day) < (self.birth_date.month, self.birth_date.day))
            )

            if age_at_ascent < self.min_age:
                errors.append(
                    self._format_rejection(
                        ascent, f"wiek ({age_at_ascent} lat) był mniejszy niż wymagane {self.min_age} lat"
                    )
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
                    self._format_rejection(
                        ascent, f"wejście było przed wejściem regulaminu w życie ({self.start_date})"
                    )
                )
        return errors


@dataclass(frozen=True)
class MandatoryObjectsRule(BadgeRule):
    """Reguła wymagająca zdobycia konkretnych, wskazanych obiektów z puli.

    Uwaga (Zgodnie z audytem): Ta reguła obsługuje tylko warunek brzegowy
    konkretnych szczytów. Główny licznik (np. 'Zdobądź 20 szczytów')
    jest ewaluowany na poziomie głównego agregatu BadgeVersionDomain.
    """

    mandatory_peak_ids: frozenset[int]  # Zamrożony zbiór dla pełnej niemutowalności

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
            missing_list = sorted(missing_mandatory_peaks)
            return [f"Brakuje obowiązkowych obiektów o ID: {missing_list}"]

        return []


@dataclass(frozen=True)
class GroupedAlternativesRule(BadgeRule):
    """Zasada 'Wiaderek' dla odznak wymagających zdobycia obiektów z wielu grup.

    Na przykład: Odznaka wymaga wejścia na po 1 punkcie widokowym w 30
    z 38 dostępnych pasm górskich.
    Każde pasmo to jedno 'wiaderko' (zbiór IDków).
    """

    # Lista wiaderek (każde wiaderko to zbiór int)
    # Bezpieczny, w 100% niemutowalny typ danych (Tuple of Frozensets)
    groups: tuple[frozenset[int], ...]

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
                f"Zbyt mało zaliczonych grup. Wymagano {self.min_groups_required}, "
                f"zdobyto zaledwie z {groups_completed} grup."
            ]

        return []


@dataclass(frozen=True)
class PrerequisiteBadgeRule(BadgeRule):
    """Reguła uzależniająca zdobycie odznaki od posiadania innej odznaki.

    Wymaga, aby turysta posiadał status ZDOBYTA dla innej, zdefiniowanej odznaki
    (np. wymagana Korona Sudetów, by zdobyć Sudeckiego Włóczykija).
    """

    required_badge_code: str

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Validate ascents for required badge rule.

        This rule requires verification of tourist's badge history, which is not
        available at ascent validation level. Returns empty list to allow parallel
        peak collection. Badge possession verification occurs at award level.

        Args:
            ascents: List of ascents to validate

        Returns:
            Empty list (no validation errors at this level)
        """
        # TODO: Faza C - Ta reguła wymaga VerificationContext (Dostępu do historii Turysty).
        # Na poziomie walidacji samych wejść (Ascents) zwracamy pustą listę,
        # ponieważ turysta ma prawo kolekcjonować szczyty równolegle.
        # Weryfikacja posiadania innej odznaki odbędzie się na poziomie przyznawania stopnia.
        return []


@dataclass(frozen=True)
class DateWindowRule(BadgeRule):
    """Reguła zamkniętego okna czasowego (np. odznaki jubileuszowe).

    Weryfikuje, czy wejście odbyło się dokładnie pomiędzy datą początkową a końcową.
    """

    start_date: date
    end_date: date

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Validate that ascents occurred within the specified date window.

        Checks if each ascent date falls between start_date and end_date (inclusive).
        Ascents outside this window are rejected with appropriate error messages.

        Args:
            ascents: List of ascents to validate

        Returns:
            List of validation error messages for ascents outside the date window
        """
        errors = []
        for ascent in ascents:
            if not (self.start_date <= ascent.ascent_date <= self.end_date):
                errors.append(
                    self._format_rejection(
                        ascent,
                        f"wejście ({ascent.ascent_date}) odbyło się poza wyznaczonym oknem "
                        f"jubileuszowym ({self.start_date} - {self.end_date})",
                    )
                )
        return errors


@dataclass(frozen=True)
class MaxAgeRule(BadgeRule):
    """Reguła maksymalnego wieku (np. dla odznak dziecięcych i młodzieżowych)."""

    max_age: int
    # TODO: Faza C - Zastąpić wstrzykiwaniem daty z kontekstu prawdziwego Turysty.
    birth_date: date = date(2015, 1, 1)

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Weryfikuje, czy w dniu wejścia turysta nie przekroczył maksymalnego wieku.

        Args:
            ascents: Lista wejść turysty na szczyty.

        Returns:
            Lista komunikatów o błędach w przypadku przekroczenia dozwolonego wieku.
        """
        errors = []
        for ascent in ascents:
            age_at_ascent = (
                ascent.ascent_date.year
                - self.birth_date.year
                - ((ascent.ascent_date.month, ascent.ascent_date.day) < (self.birth_date.month, self.birth_date.day))
            )

            # Odrzucamy wejścia, gdy turysta jest "za stary" na tę odznakę
            if age_at_ascent > self.max_age:
                errors.append(
                    self._format_rejection(
                        ascent,
                        f"wiek w dniu wejścia ({age_at_ascent} lat) przekroczył dopuszczalny limit {self.max_age} lat",
                    )
                )
        return errors


@dataclass(frozen=True)
class SubPoolRequirement:
    """Definicja pojedynczego podzbioru (np. pasma górskiego) dla reguł cząstkowych."""

    required_count: int
    peak_ids: frozenset[int]
    name: str = ""


@dataclass(frozen=True)
class MultiPoolRequirementRule(BadgeRule):
    """Reguła wymagająca zdobycia określonej liczby obiektów z kilku różnych podzbiorów.

    Na przykład: Odznaka wymaga łącznie 50 szczytów, ale w tym MUSI być
    min. 10 szczytów z podzbioru 'Tatry' i min. 10 z podzbioru 'Sudety'.
    """

    pools: tuple[SubPoolRequirement, ...]

    def validate(self, ascents: list[Ascent]) -> list[str]:
        """Weryfikuje, czy zdobyto odpowiednią liczbę obiektów z każdego podzbiorów.

        Args:
            ascents: Lista wejść na szczyty.

        Returns:
            Lista komunikatów o błędach (niespełnionych wymogach dla podzbiorów)
            lub pusta lista, jeśli wszystkie wymogi zostały spełnione.
        """
        errors = []
        climbed_peak_ids = {ascent.peak_id for ascent in ascents}

        for pool in self.pools:
            # Sprawdzamy część wspólną wejść i konkretnego podzbioru
            climbed_in_pool = climbed_peak_ids.intersection(pool.peak_ids)

            if len(climbed_in_pool) < pool.required_count:
                name_str = f" z grupy '{pool.name}'" if pool.name else " z wymaganej grupy"
                errors.append(
                    f"Wymagano min. {pool.required_count} obiektów{name_str}, zdobyto tylko {len(climbed_in_pool)}."
                )

        return errors

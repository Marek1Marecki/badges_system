"""Reguły biznesowe zdobywania odznak (Wzorzec Strategii)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from domain.value_objects.ascent import Ascent
from domain.value_objects.verification_context import VerificationContext


class BadgeRule(ABC):
    """Bazowy interfejs dla wszystkich reguł."""

    @abstractmethod
    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Zwraca listę błędów.

        Pusta lista oznacza spełnienie reguły.
                Args:
                  ascents: Lista wejść na szczyty.
                  context: Kontekst weryfikacyjny.
                  ascents: list[Ascent]:
                  context: VerificationContext:
                  ascents: list[Ascent]:
                  context: VerificationContext:

                Returns:
                  : Lista błędów w postaci ciągów znaków.
        """

    @staticmethod
    def _format_rejection(ascent: Ascent, reason: str) -> str:
        """Helper ujednolicający komunikaty o odrzuceniu konkretnego wejścia.

        Args:
          ascent: Ascent:
          reason: str:
          ascent: Ascent:
          reason: str:

        Returns:
        """
        return f"Wejście na obiekt (ID: {ascent.peak_id}, Data: {ascent.ascent_date}) odrzucone: {reason}."


@dataclass(frozen=True)
class TimeLimitRule(BadgeRule):
    """Reguła określająca limit czasu na ukończenie zdobywania."""

    limit_in_years: int

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Sprawdza czas między pierwszym a ostatnim wejściem.

        Args:
          ascents: Lista wejść do sprawdzenia.
          context: Kontekst weryfikacyjny (niewykorzystywany w tej regule).
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o błędach w przypadku przekroczenia czasu.
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
    """Reguła wymagająca przynależności do klubu (np.

    Klub Zdobywców KGP).
    Tylko wejścia (Ascents) zarejestrowane PO dacie dołączenia turysty do
    klubu mogą być zaliczone na poczet tej odznaki.

    Args:

    Returns:
    """

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Sprawdza, czy wejścia są późniejsze niż data dołączenia do klubu.

        Args:
          ascents: Lista wejść do sprawdzenia.
          context: Kontekst z datami dołączenia turysty do klubów.
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o błędach dla wejść sprzed daty dołączenia.
        """
        if not context.club_join_dates:
            return ["Wymagana przynależność do klubu, a profil turysty nie posiada żadnej."]

        earliest_join_date = min(context.club_join_dates.values())
        errors = []
        for ascent in ascents:
            if ascent.ascent_date < earliest_join_date:
                errors.append(
                    self._format_rejection(ascent, f"wejście przed dołączeniem do klubu ({earliest_join_date})")
                )
        return errors


@dataclass(frozen=True)
class MinAgeRule(BadgeRule):
    """Reguła minimalnego wieku wymagana do zdobywania odznaki.

    Weryfikuje, czy turysta w dniu wejścia na szczyt miał ukończony
    określony wiek (np. 8 lat).

    Args:

    Returns:
    """

    min_age: int

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Sprawdza, czy wiek w dniu wejścia spełnia minimalny próg.

        Args:
          ascents: Lista wejść do sprawdzenia.
          context: Kontekst z datą urodzenia turysty.
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o błędach dla wejść poniżej wymaganego wieku.
        """
        # ZMIANA BIZNESOWA: Brak daty urodzenia traktujemy jako domyślną pełnoletność.
        # Ufamy turyście, przenosząc ciężar ewentualnego oszustwa na weryfikatora PTTK.
        if not context.tourist_birth_date:
            return []  # Przepuszczamy bez błędu!

        errors = []
        for ascent in ascents:
            age_at_ascent = (
                ascent.ascent_date.year
                - context.tourist_birth_date.year
                - (
                    (ascent.ascent_date.month, ascent.ascent_date.day)
                    < (context.tourist_birth_date.month, context.tourist_birth_date.day)
                )
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

    Args:

    Returns:
    """

    start_date: date

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Sprawdza, czy wejścia są późniejsze niż data wejścia regulaminu.

        Args:
          ascents: Lista wejść do sprawdzenia.
          context: Kontekst weryfikacyjny (niewykorzystywany w tej regule).
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o błędach dla wejść sprzed daty startowej.
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

    Args:

    Returns:
    """

    mandatory_peak_ids: frozenset[int]  # Zamrożony zbiór dla pełnej niemutowalności

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Sprawdza, czy turysta zdobył wszystkie obowiązkowe obiekty.

        Args:
          ascents: Lista wszystkich wejść turysty.
          context: Kontekst weryfikacyjny (niewykorzystywany w tej regule).
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o brakujących obowiązkowych szczytach lub pusta lista.
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

    Args:

    Returns:
    """

    # Lista wiaderek (każde wiaderko to zbiór int)
    # Bezpieczny, w 100% niemutowalny typ danych (Tuple of Frozensets)
    groups: tuple[frozenset[int], ...]

    # Ile wiaderek (grup) trzeba zaliczyć (z każdego min. 1 obiekt)
    min_groups_required: int

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Zlicza, ile grup (wiaderek) zawiera przynajmniej jedno zdobyte wejście.

        Args:
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
        """
        climbed_peak_ids = {ascent.peak_id for ascent in ascents}

        groups_completed = sum(1 for group in self.groups if group.intersection(climbed_peak_ids))

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

    Args:

    Returns:
    """

    required_badge_code: str

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Validate ascents for required badge rule.

        This rule requires verification of tourist's badge history, which is not
        available at ascent validation level. Returns empty list to allow parallel
        peak collection. Badge possession verification occurs at award level.

        Args:
          ascents: List of ascents to validate
          context: Verification context containing completed badge codes
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Empty list (no validation errors at this level)
        """
        if self.required_badge_code not in context.completed_badge_codes:
            return [f"Brak wymaganej ukończonej odznaki: {self.required_badge_code}"]
        return []


@dataclass(frozen=True)
class DateWindowRule(BadgeRule):
    """Reguła zamkniętego okna czasowego (np.

    odznaki jubileuszowe).
    Weryfikuje, czy wejście odbyło się dokładnie pomiędzy datą początkową a końcową.

    Args:

    Returns:
    """

    start_date: date
    end_date: date

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Validate that ascents occurred within the specified date window.

        Checks if each ascent date falls between start_date and end_date (inclusive).
        Ascents outside this window are rejected with appropriate error messages.

        Args:
          ascents: List of ascents to validate
          context: Verification context containing additional information
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : List of validation error messages for ascents outside the date window
        """
        errors = []
        for ascent in ascents:
            if not (self.start_date <= ascent.ascent_date <= self.end_date):
                errors.append(
                    self._format_rejection(ascent, f"wejście poza oknem ({self.start_date} - {self.end_date})")
                )
        return errors


@dataclass(frozen=True)
class MaxAgeRule(BadgeRule):
    """Reguła maksymalnego wieku (np.

    dla odznak dziecięcych i młodzieżowych).
    """

    max_age: int

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Weryfikuje, czy w dniu wejścia turysta nie przekroczył maksymalnego wieku.

        Args:
          ascents: Lista wejść turysty na szczyty.
          context: Kontekst weryfikacyjny zawierający informacje o turysty.
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o błędach w przypadku przekroczenia dozwolonego wieku.
        """
        if not context.tourist_birth_date:
            return ["Wymagany maksymalny wiek, a profil turysty nie posiada zdefiniowanej daty urodzenia."]

        errors = []
        for ascent in ascents:
            age_at_ascent = (
                ascent.ascent_date.year
                - context.tourist_birth_date.year
                - (
                    (ascent.ascent_date.month, ascent.ascent_date.day)
                    < (context.tourist_birth_date.month, context.tourist_birth_date.day)
                )
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
    """Definicja pojedynczego podzbioru (np.

    pasma górskiego) dla reguł cząstkowych.
    """

    required_count: int
    peak_ids: frozenset[int]
    name: str = ""


@dataclass(frozen=True)
class MultiPoolRequirementRule(BadgeRule):
    """Reguła wymagająca zdobycia określonej liczby obiektów z kilku różnych podzbiorów.

    Na przykład: Odznaka wymaga łącznie 50 szczytów, ale w tym MUSI być
    min. 10 szczytów z podzbioru 'Tatry' i min. 10 z podzbioru 'Sudety'.

    Args:

    Returns:
    """

    pools: tuple[SubPoolRequirement, ...]

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Weryfikuje, czy zdobyto odpowiednią liczbę obiektów z każdego podzbiorów.

        Args:
          ascents: Lista wejść na szczyty.
          context: Kontekst weryfikacyjny zawierający informacje o turysty.
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o błędach (niespełnionych wymogach dla podzbiorów)
          : Lista komunikatów o błędach (niespełnionych wymogach dla podzbiorów)
          lub pusta lista, jeśli wszystkie wymogi zostały spełnione.
        """
        errors = []
        climbed_peak_ids = {a.peak_id for a in ascents}
        for pool in self.pools:
            climbed_in_pool = climbed_peak_ids.intersection(pool.peak_ids)
            if len(climbed_in_pool) < pool.required_count:
                name_str = f" z grupy '{pool.name}'" if pool.name else " z wymaganej grupy"
                errors.append(
                    f"Wymagano min. {pool.required_count} obiektów{name_str}, zdobyto {len(climbed_in_pool)}."
                )
        return errors


@dataclass(frozen=True)
class RegionCountRule(BadgeRule):
    """Reguła typu Wildcard (ADR-012).

    Zlicza szczyty na podstawie regionów CQRS.
    """

    region_id: int
    required_count: int

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        """Weryfikuje minimalną liczbę wejść przypisanych do wskazanego regionu CQRS.

        Args:
          ascents: Lista wejść turysty, potencjalnie z region_ids.
          context: Kontekst weryfikacyjny (niewykorzystywany w tej regule).
          ascents: list[Ascent]:
          context: VerificationContext:
          ascents: list[Ascent]:
          context: VerificationContext:

        Returns:
          : Lista komunikatów o błędach, gdy liczba wejść z regionu jest za mała.
        """
        valid_ascents = [a for a in ascents if self.region_id in a.region_ids]
        if len(valid_ascents) < self.required_count:
            return [
                f"Wymagano {self.required_count} obiektów z regionu {self.region_id}, zdobyto {len(valid_ascents)}."
            ]
        return []

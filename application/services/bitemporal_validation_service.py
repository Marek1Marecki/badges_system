"""Serwis Aplikacyjny: Weryfikacja Bitemporalna (Invariant T-01, T-03).

AUDYT-017: Logika weryfikacji, że data wejścia turysty mieści się w oknie
życia obiektu (`existence_start` … `existence_end`), była **duplikowana**
między `LogAscentUseCase` a pętlą `BulkLogAscentsUseCase`.

Ta klasa jest **czystym odkładnikiem tej logiki**:
- `validate_single`  — dla `LogAscentUseCase` (pojedynczy peak).
- `validate_batch`   — dla `BulkLogAscentsUseCase` (grupowo, optymalizacja N+1).

Serwis opiera się wyłącznie na `AscentLogRepositoryPort` (port aplikacyjny),
dlatego nie zmusza domeny do znajomości infrastruktury ani odwrotnie.

Zasada T-01 (existence window) oraz T-03 (future-date) są invariants
aplikacji — nie są encjami ani value-objectami, więc nie trafiają do `domain`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from application.dto.ascent_dto import AscentRequestDTO
from application.exceptions import BitemporalTimeError, UseCaseError
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import AscentLogRepositoryPort


@dataclass(frozen=True, slots=True)
class BitemporalViolation:
    """Jedna przyczyna odrzucenia wejścia w trybie batch.

    `peak_id` + `reason` — nie podnosimy własnego wyjątku, bo w batch
    chcemy gromadzić wszystkie odrzucenia (Partial Success).
    """

    peak_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class BitemporalValidationResult:
    """Wynik walidacji batch: co przeszło, a co odrzucono."""

    accepted: list[AscentRequestDTO]
    violations: list[BitemporalViolation]

    @property
    def has_violations(self) -> bool:
        """Zwraca True, gdy walidacja znalezła jakiekolwiek naruszenia."""
        return bool(self.violations)


class BitemporalValidationService:
    """Centralny serwis weryfikacji okna życia obiektu (T-01, T-03).

    Serwis jest bezzstanowy względem cyklu życia — zależy wyłącznie od
    portu repozytorium i portu zegara (T-03). Może być wstrzykiwany jako
    singleton / request-scoped do Use Case'y.
    """

    def __init__(
        self,
        ascent_repo: AscentLogRepositoryPort,
        clock: ClockPort,
    ) -> None:
        """Inicjalizuje serwis weryfikacji bitemporalnej z portem repozytorium i zegarem."""
        self._ascent_repo = ascent_repo
        self._clock = clock

    def validate_single(self, peak_id: int, ascent_date: date) -> None:
        """Walidacja T-01 + T-03 dla jednego wejścia.

        Raises:
            UseCaseError: Gdy peak nie istnieje (T-01 brak lifespan)
                albo data jest z przyszłości (T-03).
            BitemporalTimeError: Gdy wejście wykracza poza okno życia
                obiektu (T-01).
        """
        self._assert_not_future(ascent_date)

        lifespan = self._ascent_repo.get_object_lifespan(peak_id)
        if lifespan is None:
            raise UseCaseError(f"Obiekt o ID {peak_id} nie istnieje w bazie.")

        existence_start, existence_end = lifespan
        self._check_window(ascent_date, existence_start, existence_end)

    def validate_batch(self, ascents: Sequence[AscentRequestDTO]) -> BitemporalValidationResult:
        """Walidacja T-01 + T-03 dla wielu wejść (optymalizacja N+1).

        Pobiera ramy bitemporalne grupowo w jednym zapytaniu SQL,
        a następnie sprawdza każde wejście offline.

        Returns:
            BitemporalValidationResult z listą zaakceptowanych `peak_id`
            i listą naruszeń (częściowy sukces — nie przerywa pętli).
        """
        today = self._clock.now().date()

        peak_ids = {a.peak_id for a in ascents}
        lifespans = self._ascent_repo.get_objects_lifespans(peak_ids)

        accepted: list[AscentRequestDTO] = []
        violations: list[BitemporalViolation] = []

        for ascent in ascents:
            if ascent.ascent_date > today:
                violations.append(
                    BitemporalViolation(peak_id=ascent.peak_id, reason="Data wejścia jest z przyszłości (T-03).")
                )
                continue

            lifespan = lifespans.get(ascent.peak_id)
            if lifespan is None:
                violations.append(
                    BitemporalViolation(peak_id=ascent.peak_id, reason="Obiekt nie istnieje w bazie (T-01).")
                )
                continue

            existence_start, existence_end = lifespan
            window_error = self._check_window_error(ascent.ascent_date, existence_start, existence_end)
            if window_error is not None:
                violations.append(BitemporalViolation(peak_id=ascent.peak_id, reason=window_error))
                continue

            accepted.append(ascent)

        return BitemporalValidationResult(accepted=accepted, violations=violations)

    # --- Prywatne helpery (dzielą logikę T-01 / T-03) ---

    def _assert_not_future(self, ascent_date: date) -> None:
        today = self._clock.now().date()
        if ascent_date > today:
            raise UseCaseError(f"Data wejścia ({ascent_date}) nie może być z przyszłości.")

    @staticmethod
    def _check_window(ascent_date: date, existence_start: date | None, existence_end: date | None) -> None:
        """Rzuci BitemporalTimeError (T-01) jeśli poza oknem — tryb `validate_single`."""
        if existence_start and ascent_date < existence_start:
            raise BitemporalTimeError(f"Obiekt nie istniał w dacie {ascent_date}.")
        if existence_end and ascent_date > existence_end:
            raise BitemporalTimeError(f"Obiekt został wyłączony lub zniszczony po {existence_end}.")

    @staticmethod
    def _check_window_error(ascent_date: date, existence_start: date | None, existence_end: date | None) -> str | None:
        """Zwraca opis naruszenia T-01 lub `None` gdy OK — tryb `validate_batch`."""
        if existence_start and ascent_date < existence_start:
            return "Obiekt nie istniał w tej dacie (T-01)."
        if existence_end and ascent_date > existence_end:
            return "Obiekt został zniszczony/wyłączony (T-01)."
        return None

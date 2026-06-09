"""Przypadek użycia: Logowanie wejścia turysty (AscentLog).

Zgodnie z US-C03 i Invariantem T-01: Use case weryfikuje bitemporalność obiektu PRZED zapisem do bazy.
Zgodnie z Invariantem T-03: Odrzuca wejścia z przyszłości.
Zgodnie z Invariantem D-04: Blokuje zapisywanie duplikatów dla danego dnia.
"""

from application.dto.ascent_dto import AscentInputDTO
from application.exceptions import BitemporalTimeError, ConflictError, UseCaseError
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import AscentLogRepositoryPort


class LogAscentUseCase:
    """Zapisuje log wejścia turysty na szczyt z uwzględnieniem obostrzeń bitemporalnych i limitów."""

    def __init__(
        self,
        ascent_repository: AscentLogRepositoryPort,
        clock: ClockPort,
    ) -> None:
        """Wstrzykuje repozytorium wejść oraz dostawcę czasu (ClockPort)."""
        self._ascent_repo = ascent_repository
        self._clock = clock

    def execute(self, user_id: int, dto: AscentInputDTO) -> int:
        """Wykonuje operację logowania wejścia.

        Args:
            user_id: ID turysty z kontekstu sesji (API).
            dto: Zwalidowane dane wejściowe.

        Returns:
            ID utworzonego logu wejścia.

        Raises:
            UseCaseError: Gdy data wybiega w przyszłość (T-03) lub obiekt nie istnieje.
            BitemporalTimeError: Jeśli data wejścia wykracza poza cykl życia obiektu (T-01).
            ConflictError: Jeśli turysta zalogował już ten obiekt tego samego dnia (D-04).
        """
        # 1. Zakaz logowania w przyszłości (Invariant T-03)
        today = self._clock.now().date()
        if dto.ascent_date > today:
            raise UseCaseError(f"Data wejścia ({dto.ascent_date}) nie może być z przyszłości.")

        # 2. Weryfikacja Bitemporalna (Invariant T-01)
        lifespan = self._ascent_repo.get_object_lifespan(dto.peak_id)
        if lifespan is None:
            raise UseCaseError(f"Obiekt turystyczny (ID: {dto.peak_id}) nie istnieje.")

        existence_start, existence_end = lifespan

        if existence_start and dto.ascent_date < existence_start:
            raise BitemporalTimeError(
                f"Niewiarygodna data: Obiekt powstał {existence_start}, a data wejścia to {dto.ascent_date}."
            )

        if existence_end and dto.ascent_date > existence_end:
            raise BitemporalTimeError(
                f"Niewiarygodna data: Obiekt przestał istnieć {existence_end}, a data wejścia to {dto.ascent_date}."
            )

        # 3. Zabezpieczenie przed duplikatami / Upsert (Invariant D-04)
        if self._ascent_repo.ascent_exists(user_id=user_id, peak_id=dto.peak_id, ascent_date=dto.ascent_date):
            raise ConflictError(
                f"Wejście na obiekt {dto.peak_id} w dniu {dto.ascent_date} zostało już wcześniej zalogowane."
            )

        # 4. Zapis faktu (Delegacja do adaptera bazy danych)
        ascent_id = self._ascent_repo.save_ascent(
            user_id=user_id,
            peak_id=dto.peak_id,
            ascent_date=dto.ascent_date,
        )

        # Wskazówka implementacyjna Fazy C:
        # Zgodnie z Event-Driven Cache Invalidation, warstwa API wywołująca ten UseCase
        # powinna po pomyślnym wykonaniu uruchomić zadanie w Celery odświeżające Ranking Potencjału.
        return ascent_id

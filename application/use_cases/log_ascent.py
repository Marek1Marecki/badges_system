"""Przypadek użycia: Logowanie wejścia turysty (AscentLog).

Zgodnie z US-C03 i Invariantem T-01: Use case weryfikuje bitemporalność obiektu PRZED zapisem do bazy. Zgodnie z
Invariantem T-03: Odrzuca wejścia z przyszłości. Zgodnie z Invariantem D-04: Blokuje zapisywanie duplikatów dla danego
dnia.
"""

from application.dto.ascent_dto import AscentInputDTO
from application.exceptions import BitemporalTimeError, ConflictError, UseCaseError
from application.ports.clock_port import ClockPort
from application.ports.event_publisher_port import DomainEventPublisherPort
from application.ports.uow_port import UnitOfWorkPort
from application.ports.user_progress_port import AscentLogRepositoryPort, TouristProfileRepositoryPort
from application.services.poi_scoring_service import PoiScoringService
from domain.events import UserProgressStateChanged


class LogAscentUseCase:
    """Zapisuje log wejścia turysty na szczyt z uwzględnieniem obostrzeń bitemporalnych i limitów."""

    def __init__(
        self,
        ascent_repository: AscentLogRepositoryPort,
        profile_repository: TouristProfileRepositoryPort,
        poi_service: PoiScoringService,
        clock: ClockPort,
        uow: UnitOfWorkPort,
        event_publisher: DomainEventPublisherPort,
    ) -> None:
        """Inicjuje przypadek użycia logowania wejścia."""
        self._ascent_repo = ascent_repository
        self._profile_repo = profile_repository
        self._poi_service = poi_service
        self._clock = clock
        self._uow = uow
        self._event_publisher = event_publisher

    def execute(self, profile_id: int, dto: AscentInputDTO) -> int:
        """Wykonuje operację logowania wejścia.

        Args:
          profile_id: ID turysty z kontekstu sesji (API).
          dto: Zwalidowane dane wejściowe.
          profile_id: int:
          dto: AscentInputDTO:
          profile_id: int:
          dto: AscentInputDTO:

        Returns:
          : ID utworzonego logu wejścia.

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
            raise UseCaseError(f"Obiekt o ID {dto.peak_id} nie istnieje w bazie.")

        existence_start, existence_end = lifespan
        if existence_start and dto.ascent_date < existence_start:
            raise BitemporalTimeError(f"Obiekt nie istniał w dacie {dto.ascent_date}.")
        if existence_end and dto.ascent_date > existence_end:
            raise BitemporalTimeError(f"Obiekt został wyłączony lub zniszczony po {existence_end}.")

        # 3. Zabezpieczenie przed duplikatami / Upsert (Invariant D-04)
        if self._ascent_repo.ascent_exists(profile_id=profile_id, peak_id=dto.peak_id, ascent_date=dto.ascent_date):
            raise ConflictError(
                f"Wejście na obiekt {dto.peak_id} w dniu {dto.ascent_date} zostało już wcześniej zalogowane."
            )

        # 4. Krok: Atomowy zapis i Powiadomienie (Unit Of Work)
        with self._uow:
            ascent_id = self._ascent_repo.save_ascent(
                profile_id=profile_id,
                peak_id=dto.peak_id,
                ascent_date=dto.ascent_date,
            )
            # Uruchamiamy powiadomienie (odpali to Celery, gdy transakcja z commituje się w db)
            self._event_publisher.publish(UserProgressStateChanged(profile_id=profile_id))

        # Wskazówka implementacyjna Fazy C:
        # Zgodnie z Event-Driven Cache Invalidation, warstwa API wywołująca ten UseCase
        # powinna po pomyślnym wykonaniu uruchomić zadanie w Celery odświeżające Ranking Potencjału.
        return ascent_id

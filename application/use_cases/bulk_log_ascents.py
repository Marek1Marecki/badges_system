"""Przypadek użycia: Zbiorcze logowanie wejść z analizatora GPX (US-C17).

Realizuje Invarianty:
- T-01: Odrzuca wejścia przed budową lub po zniszczeniu obiektu.
- T-03: Odrzuca wejścia z przyszłości.
- D-04: Idempotentny zapis przez Adapter bazy (Upsert/Ignore).

Implementuje wzorzec Event Throttling (częściowy sukces)
oraz unika błędu N+1 odpytując ramy bitemporalne grupowo.

Gwarantuje tzw. Partial Success - zwraca co się udało zapisać, a co odrzucono.
"""

from application.dto.ascent_dto import AscentInputDTO
from application.ports.event_publisher_port import DomainEventPublisherPort
from application.ports.uow_port import UnitOfWorkPort
from application.ports.user_progress_port import AscentLogRepositoryPort
from application.services.bitemporal_validation_service import BitemporalValidationService
from domain.events import UserProgressStateChanged


class BulkLogAscentsUseCase:
    """Odpowiada za masowe zrzucanie logów do bazy (np.

    ze śladu GPX).
    """

    def __init__(
        self,
        ascent_repository: AscentLogRepositoryPort,
        bitemporal_service: BitemporalValidationService,
        uow: UnitOfWorkPort,
        event_publisher: DomainEventPublisherPort,
    ) -> None:
        """Inicjalizuje przypadek użycia masowego importu wejść."""
        self._ascent_repo = ascent_repository
        self._bitemporal_service = bitemporal_service
        self._uow = uow
        self._event_publisher = event_publisher

    def execute(self, profile_id: int, ascents: list[AscentInputDTO]) -> dict[str, int | list[dict[str, str]]]:
        """Przetwarza listę wejść, blokując nieistniejące obiekty (T-01, T-03).

        Zapisuje tylko poprawne logi i zwraca raport w trybie Partial Success.

        Args:
          profile_id: ID profilu turysty.
          ascents: Lista wejść do zapisania.

        Returns:
          Raport z liczbą zapisanych wejść i listą błędów.
        """
        # AUDYT-017: Bitemporalna weryfikacja (T-01, T-03) + N+1 batch
        # pobierająca ramy życia grupowo została wyodrębniona do
        # BitemporalValidationService — single source of truth.
        validation_result = self._bitemporal_service.validate_batch(ascents)

        errors = [{"peak_id": str(v.peak_id), "reason": v.reason} for v in validation_result.violations]
        valid_ascents = validation_result.accepted

        # 3. Zapis i Publikacja (Unit Of Work)
        if valid_ascents:
            with self._uow:
                # Baza sama ignoruje duplikaty na podstawie Constraintu (D-04)
                saved = self._ascent_repo.bulk_save_ascents(profile_id, valid_ascents)

                # Zdarzenie odpalane TYLKO gdy udało się coś zapisać
                self._event_publisher.publish(UserProgressStateChanged(profile_id=profile_id))
        else:
            saved = 0

        # Wymuszamy typowanie list[dict[str,str]] żeby oszukać Pydantica w DTO zwrotnej
        typed_errors: list[dict[str, str]] = [
            {"peak_id": str(e["peak_id"]), "reason": str(e["reason"])} for e in errors
        ]

        return {"saved_count": saved, "errors": typed_errors}

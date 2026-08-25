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
from application.ports.clock_port import ClockPort
from application.ports.event_publisher_port import DomainEventPublisherPort
from application.ports.uow_port import UnitOfWorkPort
from application.ports.user_progress_port import AscentLogRepositoryPort
from domain.events import UserProgressStateChanged


class BulkLogAscentsUseCase:
    """Odpowiada za masowe zrzucanie logów do bazy (np.

    ze śladu GPX).
    """

    def __init__(
        self,
        ascent_repository: AscentLogRepositoryPort,
        clock: ClockPort,
        uow: UnitOfWorkPort,
        event_publisher: DomainEventPublisherPort,
    ) -> None:
        """Inicjuje przypadek użycia masowego importu wejść."""
        self._ascent_repo = ascent_repository
        self._clock = clock
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
        today = self._clock.now().date()
        errors = []
        valid_ascents = []

        # 1. Optymalizacja N+1: Pobieramy daty życia grupowo (jeden strzał SQL)
        peak_ids = {a.peak_id for a in ascents}
        lifespans = self._ascent_repo.get_objects_lifespans(peak_ids)

        # 2. Walidacja T-01 i T-03
        for ascent in ascents:
            if ascent.ascent_date > today:
                errors.append({"peak_id": str(ascent.peak_id), "reason": "Data z przyszłości."})
                continue

            lifespan = lifespans.get(ascent.peak_id)
            if not lifespan:
                errors.append({"peak_id": str(ascent.peak_id), "reason": "Obiekt nie istnieje."})
                continue

            start_date, end_date = lifespan
            if start_date and ascent.ascent_date < start_date:
                errors.append({"peak_id": str(ascent.peak_id), "reason": "Obiekt nie istniał w tej dacie."})
                continue
            if end_date and ascent.ascent_date > end_date:
                errors.append({"peak_id": str(ascent.peak_id), "reason": "Obiekt został zniszczony/wyłączony."})
                continue

            valid_ascents.append(ascent)

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

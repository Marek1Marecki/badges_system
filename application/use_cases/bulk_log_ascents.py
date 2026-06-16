"""Przypadek użycia: Zbiorcze logowanie wejść z analizatora GPX.

Realizuje Invarianty:
- T-01: Odrzuca wejścia przed budową lub po zniszczeniu obiektu.
- T-03: Odrzuca wejścia z przyszłości.
- D-04: Idempotentny zapis przez Adapter bazy (Upsert/Ignore).

Gwarantuje tzw. Partial Success - zwraca co się udało zapisać, a co odrzucono.
"""

from application.dto.ascent_dto import AscentInputDTO, BulkAscentResultDTO
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import AscentLogRepositoryPort


class BulkLogAscentsUseCase:
    """Zbiorczo zapisuje historię wycieczki, walidując daty w locie."""

    def __init__(
        self,
        ascent_repository: AscentLogRepositoryPort,
        clock: ClockPort,
    ) -> None:
        """Initialize the use case with required dependencies."""
        self._ascent_repo = ascent_repository
        self._clock = clock

    def execute(self, user_id: int, ascents: list[AscentInputDTO]) -> BulkAscentResultDTO:
        """Sprawdza i masowo zapisuje wejścia, wyłapując logiczne błędy."""
        if not ascents:
            return BulkAscentResultDTO(saved_count=0, errors=[])

        today = self._clock.now().date()
        valid_ascents = []
        errors = []

        # 1. OPTYMALIZACJA N+1: Odpytujemy bazę o wszystkie cykle życia jednym strzałem
        peak_ids = {a.peak_id for a in ascents}
        lifespans = self._ascent_repo.get_objects_lifespans(peak_ids)

        # 2. WALIDACJA WEJŚĆ (Filtrowanie i błędy częściowe)
        for dto in ascents:
            # Zakaz logowania w przyszłości (T-03)
            if dto.ascent_date > today:
                errors.append(
                    {"peak_id": dto.peak_id, "reason": f"Data wejścia ({dto.ascent_date}) jest z przyszłości."}
                )
                continue

            # Sprawdzenie bitemporalności (T-01)
            lifespan = lifespans.get(dto.peak_id)
            if lifespan is None:
                errors.append({"peak_id": dto.peak_id, "reason": "Obiekt nie istnieje w systemie."})
                continue

            existence_start, existence_end = lifespan

            if existence_start and dto.ascent_date < existence_start:
                errors.append({"peak_id": dto.peak_id, "reason": f"Obiekt powstał {existence_start}."})
                continue

            if existence_end and dto.ascent_date > existence_end:
                errors.append({"peak_id": dto.peak_id, "reason": f"Obiekt zniszczono/zamknięto {existence_end}."})
                continue

            valid_ascents.append(dto)

        # 3. ZAPIS DO BAZY (Tylko poprawne)
        saved_count = 0
        if valid_ascents:
            saved_count = self._ascent_repo.bulk_save_ascents(user_id, valid_ascents)

        # Powiadamiamy API o wyniku. API zadecyduje, czy odpalić Taska Celery (1 raz!)
        return BulkAscentResultDTO(
            saved_count=saved_count,
            errors=errors,
        )

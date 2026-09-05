"""Fake repozytorium do testów postępów i wejść turysty."""

from datetime import date
from typing import Any

from application.dto.ascent_dto import AscentDTO
from application.dto.user_context_dto import BadgeProgressDTO, TouristProfileDTO
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)


class FakeTouristRepository(
    TouristProfileRepositoryPort,
    AscentLogRepositoryPort,
    UserProgressRepositoryPort,
):
    """Zunifikowany Fake na potrzeby szybkiego testowania Use Case'ów Fazy C."""

    def __init__(self) -> None:
        self.profiles: dict[int, TouristProfileDTO] = {}
        self.ascents: list[dict[str, Any]] = []
        self.progresses: dict[int, BadgeProgressDTO] = {}
        self._next_ascent_id = 1
        self._next_progress_id = 1

    # --- TouristProfileRepositoryPort ---
    def get_profile(self, profile_id: int) -> TouristProfileDTO | None:
        return self.profiles.get(profile_id)

    # --- AscentLogRepositoryPort ---
    def get_object_lifespan(self, object_id: int) -> tuple[date | None, date | None] | None:
        return (None, None)  # W testach domyślnie obiekt żyje wiecznie

    def ascent_exists(self, profile_id: int, object_id: int, ascent_date: date) -> bool:
        for a in self.ascents:
            if a["profile_id"] == profile_id and a["peak_id"] == object_id and a["ascent_date"] == ascent_date:
                return True
        return False

    def get_oldest_ascent_date(self, profile_id: int, badge_code: str) -> date | None:
        profile_ascents = [a["ascent_date"] for a in self.ascents if a["profile_id"] == profile_id]
        if profile_ascents:
            return min(profile_ascents)
        return None

    def save_ascent(self, profile_id: int, object_id: int, ascent_date: date) -> int:
        ascent_id = self._next_ascent_id
        self._next_ascent_id += 1
        self.ascents.append(
            {
                "id": ascent_id,
                "profile_id": profile_id,
                "peak_id": object_id,
                "ascent_date": ascent_date,
            }
        )
        return ascent_id

    def get_unconsumed_ascents(self, profile_id: int, badge_code: str, cutoff_date: date | None) -> list[AscentDTO]:
        result = []
        for a in self.ascents:
            if a["profile_id"] == profile_id:
                if cutoff_date and a["ascent_date"] <= cutoff_date:
                    continue
                result.append(AscentDTO(object_id=a["peak_id"], ascent_date=a["ascent_date"], region_ids=frozenset()))
        return result

    def get_all_ascents_for_user(self, profile_id: int) -> list[AscentDTO]:
        result = []
        for a in self.ascents:
            if a["profile_id"] == profile_id:
                result.append(AscentDTO(object_id=a["peak_id"], ascent_date=a["ascent_date"], region_ids=frozenset()))
        return result

    # --- UserProgressRepositoryPort ---
    def get_all_unarchived_progresses(self, profile_id: int) -> list[BadgeProgressDTO]:
        return [p for p in self.progresses.values() if p.profile_id == profile_id]

    def get_progress(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> BadgeProgressDTO | None:
        for p in self.progresses.values():
            if p.profile_id == profile_id and p.badge_code == badge_code and p.cycle_number == cycle_number:
                return p
        return None

    def start_progress(self, profile_id: int, badge_code: str, version_id: int, cycle_number: int = 1) -> int:
        prog_id = self._next_progress_id
        self._next_progress_id += 1
        dto = BadgeProgressDTO(
            progress_id=prog_id,
            profile_id=profile_id,
            badge_code=badge_code,
            version_id=version_id,
            cycle_number=cycle_number,
            domain_status="NOT_STARTED",
            logistic_status=None,
            logistic_status_date=None,
        )
        self.progresses[prog_id] = dto
        return prog_id

    def update_domain_status(self, progress_id: int, status: str) -> None:
        if progress_id in self.progresses:
            # Pydantic jest zamrożony, trzeba stworzyć nową instancję z zaktualizowanym polem
            p = self.progresses[progress_id]
            self.progresses[progress_id] = BadgeProgressDTO(
                progress_id=p.progress_id,
                profile_id=p.profile_id,
                badge_code=p.badge_code,
                version_id=p.version_id,
                cycle_number=p.cycle_number,
                domain_status=status,
                logistic_status=p.logistic_status,
                logistic_status_date=p.logistic_status_date,
            )

    def update_logistic_status(self, progress_id: int, logistic_status: str, status_date: date) -> None:
        if progress_id in self.progresses:
            p = self.progresses[progress_id]
            self.progresses[progress_id] = BadgeProgressDTO(
                progress_id=p.progress_id,
                profile_id=p.profile_id,
                badge_code=p.badge_code,
                version_id=p.version_id,
                cycle_number=p.cycle_number,
                domain_status=p.domain_status,
                logistic_status=logistic_status,
                logistic_status_date=status_date,
            )

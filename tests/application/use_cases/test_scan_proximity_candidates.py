"""Testy jednostkowe dla skanera bliskości (Radar)."""

from unittest.mock import MagicMock

from application.use_cases.scan_proximity_candidates import ScanProximityCandidatesUseCase


def test_scan_proximity_candidates_use_case() -> None:
    repo = MagicMock()
    # Zwraca 2 znalezione pary bliskich obiektów
    repo.find_proximity_candidates.return_value = [(1, 2, 10.0), (3, 4, 20.0)]
    # Pierwszy tworzy nową parę (True), drugi to stary wpis który już istniał (False)
    repo.create_proximity_candidate.side_effect = [True, False]

    uc = ScanProximityCandidatesUseCase(repo)
    result = uc.execute()

    assert "Utworzono 1 nowych" in result
    assert repo.create_proximity_candidate.call_count == 2

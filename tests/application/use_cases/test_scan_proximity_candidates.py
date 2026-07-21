"""Testy jednostkowe dla skanera bliskości (Radar)."""

from unittest.mock import MagicMock

from application.use_cases.scan_proximity_candidates import ScanProximityCandidatesUseCase


def test_scan_proximity_candidates_use_case() -> None:
    repo = MagicMock()
    # Zwraca 1 obiekt do przetworzenia z geometrią
    geom_mock = MagicMock()
    repo.get_unprocessed_objects.return_value = [(1, geom_mock)]
    # Zwraca 2 pobliskie obiekty
    repo.find_nearby_objects.return_value = [2, 3]
    # Zapisuje 1 nową parę (deduplikacja w adapterze)
    repo.save_candidate_pairs.return_value = 1

    uc = ScanProximityCandidatesUseCase(repo)
    result = uc.execute()

    assert "Zakończono" in result
    assert "1 nowych kandydatów" in result
    repo.get_unprocessed_objects.assert_called_once_with(limit=100)
    repo.find_nearby_objects.assert_called_once_with(1, geom_mock, distance_m=150.0)
    repo.save_candidate_pairs.assert_called_once_with(parent_id=1, child_ids=[2, 3])

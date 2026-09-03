"""Testy jednostkowe dla BadgeAwardingDomainService (Grandfather Clause)."""

from datetime import date

import pytest

from domain.services.badge_awarding_domain_service import BadgeAwardingDomainService
from domain.value_objects.verification_result import TierResult, VerificationResult


@pytest.fixture
def service() -> BadgeAwardingDomainService:
    return BadgeAwardingDomainService()


class TestBadgeAwardingDomainService:
    def test_grants_completed_when_persisted_is_completed(self, service) -> None:
        """Prawo nabytów: COMPLETED w bazie zawsze chroni turystę."""
        result = service.resolve_final_status(
            persisted_status="COMPLETED",
            domain_result=VerificationResult(
                verified=False,
                status="IN_PROGRESS",
                valid_ascents_count=2,
                tiers=[TierResult(tier_id=1, name="Standard", status="IN_PROGRESS", required_count=5)],
            ),
        )
        assert result == ("COMPLETED", True)

    def test_passes_through_domain_result_when_not_completed(self, service) -> None:
        """Gdy nie ma COMPLETED w bazie, zwraca czysty wynik domenowy."""
        domain_result = VerificationResult(
            verified=True,
            status="COMPLETED",
            valid_ascents_count=5,
            tiers=[TierResult(tier_id=1, name="Standard", status="COMPLETED", required_count=5)],
        )
        result = service.resolve_final_status(persisted_status="IN_PROGRESS", domain_result=domain_result)
        assert result == ("COMPLETED", True)

    def test_passes_through_failed_result(self, service) -> None:
        """Niezweryfikowany wynik domenowy jest przekazywany dalej."""
        errors = ["Wiek nie spełnia wymogów"]
        domain_result = VerificationResult(
            verified=False,
            status="IN_PROGRESS",
            errors=errors,
            valid_ascents_count=2,
            tiers=[TierResult(tier_id=1, name="Standard", status="IN_PROGRESS", required_count=5)],
        )
        result = service.resolve_final_status(persisted_status="IN_PROGRESS", domain_result=domain_result)
        assert result == ("IN_PROGRESS", False)
        assert errors == ["Wiek nie spełnia wymogów"]

    def test_handles_none_persisted_status(self, service) -> None:
        """Gdy persisted_status jest None (nowa subskrypcja), zwraca wynik domenowy."""
        domain_result = VerificationResult(
            verified=False,
            status="NOT_STARTED",
            valid_ascents_count=0,
        )
        result = service.resolve_final_status(persisted_status=None, domain_result=domain_result)
        assert result == ("NOT_STARTED", False)

    def test_determine_anchor_date_uses_oldest_ascent(self, service) -> None:
        """Grandfather Clause: najstarsze wejście staje się datą zakotwiczenia."""
        anchor = service.determine_anchor_date(
            oldest_ascent_date=date(2015, 6, 1),
            fallback_date=date(2026, 9, 3),
        )
        assert anchor == date(2015, 6, 1)

    def test_determine_anchor_date_uses_fallback_when_no_ascent(self, service) -> None:
        """Brak wejść → data bieżąca (fallback)."""
        anchor = service.determine_anchor_date(
            oldest_ascent_date=None,
            fallback_date=date(2026, 9, 3),
        )
        assert anchor == date(2026, 9, 3)

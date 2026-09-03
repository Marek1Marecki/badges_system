"""Testy dla DTO weryfikacji odznak."""

from application.dto.verify_badge_dto import (
    TierResultResponseDTO,
    VerifyBadgeRequestDTO,
    VerifyBadgeResponseDTO,
)


def test_verify_badge_request_dto_valid() -> None:
    """Test poprawnego utworzenia DTO żądania weryfikacji."""
    dto = VerifyBadgeRequestDTO(profile_id=1, badge_code="KGP", cycle_number=2)
    assert dto.profile_id == 1
    assert dto.badge_code == "KGP"
    assert dto.cycle_number == 2


def test_verify_badge_request_dto_default_cycle() -> None:
    """Test domyślnego numeru cyklu."""
    dto = VerifyBadgeRequestDTO(profile_id=1, badge_code="KGP")
    assert dto.cycle_number == 1


def test_verify_badge_result_dto_valid() -> None:
    """Test poprawnego utworzenia DTO wyniku weryfikacji (AUDYT-124)."""
    result = VerifyBadgeResponseDTO(
        verified=True,
        status="COMPLETED",
        valid_ascents_count=5,
        errors=[],
        tiers=[TierResultResponseDTO(tier_id=1, name="Standard", status="COMPLETED", required_count=5)],
    )
    assert result.verified is True
    assert result.status == "COMPLETED"
    assert result.tiers[0].name == "Standard"


def test_verify_badge_result_dto_defaults() -> None:
    """Domyślne pola (errors, tiers) powinny być pustymi listami."""
    result = VerifyBadgeResponseDTO(verified=False, status="IN_PROGRESS", valid_ascents_count=2)
    assert result.errors == []
    assert result.tiers == []

"""Testy dla DTO weryfikacji odznak."""

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO


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

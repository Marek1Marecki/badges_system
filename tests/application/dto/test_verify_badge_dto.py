"""Testy dla DTO weryfikacji odznak."""

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO


def test_verify_badge_request_dto_valid() -> None:
    dto = VerifyBadgeRequestDTO(user_id=1, badge_code="KGP", cycle_number=2)
    assert dto.user_id == 1
    assert dto.badge_code == "KGP"
    assert dto.cycle_number == 2


def test_verify_badge_request_dto_default_cycle() -> None:
    dto = VerifyBadgeRequestDTO(user_id=1, badge_code="KGP")
    assert dto.cycle_number == 1

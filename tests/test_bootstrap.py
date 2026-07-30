"""Testy dla warstwy bootstrap."""

from unittest.mock import patch

from bootstrap.container import configure_app, get_container, reset_container


# configure_app jest teraz aliasem dla build_container, który nie wywołuje configure_logging
@patch("infrastructure.config.AppSettings")
def test_configure_app(mock_settings) -> None:
    mock_settings.return_value.log_json = True
    mock_settings.return_value.log_level = "DEBUG"

    container = configure_app()

    # Weryfikujemy, że kontener został poprawnie zbudowany
    assert container is not None


def test_container_singleton() -> None:
    # Resetujemy kontener, by mieć czysty stan
    reset_container()

    # Wywołujemy PRAWDZIWY kontener (konstruktory naszych klas są bezpieczne i nie pytają bazy!)
    container1 = get_container()
    container2 = get_container()

    # Weryfikacja wzorca Singleton
    assert container1 is container2

    # Weryfikacja czy kontener wygenerował i zarejestrował wszystkie nasze Use Case'y
    # AppContainer to dataclass, więc używamy hasattr zamiast operatora 'in'
    expected_use_cases = [
        "evaluate_badge_progress",
        "update_badge_progress",
        "fetch_osm_data",
        "calculate_object_regions",
        "build_tourist_region_geometry",
        "scan_proximity_candidates",
        "run_osm_night_watchman",
        "log_ascent",
        "start_badge_progress",
    ]

    for uc in expected_use_cases:
        assert hasattr(container1, uc)


def test_reset_container() -> None:
    c1 = get_container()
    reset_container()
    c2 = get_container()
    assert c1 is not c2

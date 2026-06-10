"""Testy dla warstwy bootstrap."""

from unittest.mock import patch

from bootstrap.container import configure_app, get_container, reset_container


# Patchujemy u źródła (w modułach infrastruktury), a nie w module bootstrap,
# ponieważ importy w configure_app są lokalne (wewnątrz funkcji).
@patch("infrastructure.logging.configure_logging")
@patch("infrastructure.config.AppSettings")
def test_configure_app(mock_settings, mock_logging) -> None:
    mock_settings.return_value.log_json = True
    mock_settings.return_value.log_level = "DEBUG"

    configure_app()

    mock_logging.assert_called_once_with(json_mode=True, level="DEBUG")


def test_container_singleton() -> None:
    # Resetujemy kontener, by mieć czysty stan
    reset_container()

    # Wywołujemy PRAWDZIWY kontener (konstruktory naszych klas są bezpieczne i nie pytają bazy!)
    container1 = get_container()
    container2 = get_container()

    # Weryfikacja wzorca Singleton
    assert container1 is container2

    # Weryfikacja czy kontener wygenerował i zarejestrował wszystkie nasze Use Case'y
    expected_use_cases = [
        "verify_badge",
        "fetch_osm_data",
        "calculate_object_regions",
        "build_tourist_region_geometry",
        "scan_proximity_candidates",
        "run_osm_night_watchman",
        "log_ascent",
        "start_badge_progress",
    ]

    for uc in expected_use_cases:
        assert uc in container1


def test_reset_container() -> None:
    c1 = get_container()
    reset_container()
    c2 = get_container()
    assert c1 is not c2

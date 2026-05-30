"""Konfiguracja logowania dla całej aplikacji.

Zgodnie z 18-logging-monitoring.md i 14-domain-purity.md:
- Loguru jako standard (nie stdlib logging)
- Konfiguracja wyłącznie w infrastructure/ — domain/ i application/ nie logują
- JSON w produkcji (serialize=True) → gotowy pod ELK/Loki
- Czytelny format kolorowy w developmencie

Użycie w bootstrap/:
    from infrastructure.logging import configure_logging
    configure_logging(json_mode=settings.log_json, level=settings.log_level)

Użycie w adapterach infrastrukturalnych:
    from loguru import logger
    logger.info("Pobrano dane z OSM", osm_id=obj.osm_id)
"""

import sys

from loguru import logger


def configure_logging(*, json_mode: bool = False, level: str = "INFO") -> None:
    """Konfiguruje globalne logowanie aplikacji.

    Wywołać dokładnie raz w bootstrap, przed uruchomieniem jakichkolwiek
    adapterów. Kolejne wywołania nadpiszą poprzednią konfigurację.

    Args:
        json_mode: True → JSON na stdout (produkcja, ELK/Loki).
                   False → kolorowy format czytelny dla dewelopera.
        level: Minimalny poziom logowania (DEBUG/INFO/WARNING/ERROR/CRITICAL).
    """
    logger.remove()  # usuń domyślny handler Loguru

    if json_mode:
        # Produkcja: JSON na stdout, zbierany przez Docker → ELK/Loki
        logger.add(
            sys.stdout,
            level=level,
            serialize=True,  # każdy wpis jako JSON object
            backtrace=False,  # nie ujawniamy stacktrace na produkcji
            diagnose=False,
        )
    else:
        # Development: czytelny format z kolorami i lokalizacją
        logger.add(
            sys.stdout,
            level=level,
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
                "<level>{message}</level>"
            ),
            backtrace=True,
            diagnose=True,
        )

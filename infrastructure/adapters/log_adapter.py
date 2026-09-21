"""Adapter logowania oparty na Loguru — implementacja LoggingPort.

Zgodnie z 18-logging-monitoring.md:
- Loguru jest biblioteką warstwy infrastrukturalnej
- Konfiguracja logowania (stdout/stderr, JSON) w `infrastructure/logging/log_config.py`
"""

from loguru import logger

from application.ports.logging_port import LoggingPort


class LoguruLoggingAdapter(LoggingPort):
    """Adapter loguru implementujący LoggingPort dla warstwy aplikacji."""

    def info(self, message: str, *args: object) -> None:
        if args:
            logger.info(message, *args)
        else:
            logger.info(message)

    def warning(self, message: str, *args: object) -> None:
        if args:
            logger.warning(message, *args)
        else:
            logger.warning(message)

    def error(self, message: str, *args: object) -> None:
        if args:
            logger.error(message, *args)
        else:
            logger.error(message)

    def debug(self, message: str, *args: object) -> None:
        if args:
            logger.debug(message, *args)
        else:
            logger.debug(message)

    def exception(self, message: str, *args: object) -> None:
        if args:
            logger.opt(exception=True).error(message, *args)
        else:
            logger.opt(exception=True).error(message)

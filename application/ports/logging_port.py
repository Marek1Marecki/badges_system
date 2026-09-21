"""Port dla logowania w warstwie aplikacji.

Zgodnie z 14-domain-purity.md i 18-logging-monitoring.md:
- application/ nie importuje loguru ani stdlib logging
- application/ otrzymuje logger przez ten port (dependency injection)
- Implementacja (loguru) żyje w infrastructure/
"""

from typing import Protocol


class LoggingPort(Protocol):
    """Abstrakcja logowania dla warstwy aplikacji.

    Implementacja w `infrastructure/` używa loguru.
    Aplikacja używa tego interfejsu, aby nie zależeć od konkretnej biblioteki logującej.

    Pozycyjne argumenty `*args` obsługują formatowanie `{}` (loguru style).
    """

    def info(self, message: str, *args: object) -> None:
        """Loguje na poziomie INFO."""
        ...

    def warning(self, message: str, *args: object) -> None:
        """Loguje na poziomie WARNING."""
        ...

    def error(self, message: str, *args: object) -> None:
        """Loguje na poziomie ERROR."""
        ...

    def debug(self, message: str, *args: object) -> None:
        """Loguje na poziomie DEBUG."""
        ...

    def exception(self, message: str, *args: object) -> None:
        """Loguje na poziomie ERROR z pełnym tracebackiem."""
        ...

"""Hierarchia wyjątków warstwy aplikacji.

Wyjątki z tej warstwy tłumaczą błędy domenowe i infrastrukturalne
na błędy zrozumiałe dla interfejsu (np. API, CLI).
"""


class ApplicationException(Exception):
    """Bazowy wyjątek dla warstwy aplikacji."""


class UseCaseError(ApplicationException):
    """Błąd orkiestracji podczas wykonywania przypadku użycia."""

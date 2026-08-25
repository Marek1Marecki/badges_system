"""Hierarchia wyjątków warstwy aplikacji.

Wyjątki z tej warstwy tłumaczą błędy domenowe i infrastrukturalne na błędy zrozumiałe dla interfejsu (np. API, CLI).

Mapowanie na kody HTTP (RFC 7807ErrorMiddleware):     ResourceNotFoundError  → 404     ConflictError          → 409
BitemporalTimeError    → 422     UseCaseError           → 422     ApplicationException   → 500 (fallback)
"""


class ApplicationException(Exception):
    """Bazowy wyjątek dla warstwy aplikacji."""


class UseCaseError(ApplicationException):
    """Błąd orkiestracji podczas wykonywania przypadku użycia.

    Używany dla: daty z przyszłości (T-03), brak regulaminu,
    brak subskrypcji przy weryfikacji.
    Mapuje na: 422 Unprocessable Entity

    Args:

    Returns:
    """


class ResourceNotFoundError(ApplicationException):
    """Żądany zasób nie istnieje.

    Używany dla: turysta nie subskrybuje odznaki, odznaka nie istnieje w bazie.
    Mapuje na: 404 Not Found

    Args:

    Returns:
    """


class BitemporalTimeError(ApplicationException):
    """Naruszenie bitemporalnego cyklu życia obiektu turystycznego.

    Używany dla: data wejścia przed powstaniem obiektu lub po jego
    likwidacji (Invariant T-01).
    Mapuje na: 422 Unprocessable Entity

    Args:

    Returns:
    """


class ConflictError(ApplicationException):
    """Błąd w przypadku konfliktu danych.

    Używany dla: duplikat logu wejścia (D-04),
    błędne przejście stanu logistycznego.
    Mapuje na: 409 Conflict

    Args:

    Returns:
    """

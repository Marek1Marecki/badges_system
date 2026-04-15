"""Wyjątki warstwy infrastruktury.

Wyjątki z tej warstwy oznaczają błędy komunikacji z zewnętrznymi API,
błędy baz danych lub problemy z wirtualnym środowiskiem operacyjnym.
"""


class InfrastructureException(Exception):
    """Bazowy wyjątek dla wszystkich błędów w infrastrukturze."""

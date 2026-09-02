"""Wyjątki warstwy infrastruktury.

Wyjątki z tej warstwy oznaczają błędy komunikacji z zewnętrznymi API, błędy baz danych lub problemy z wirtualnym
środowiskiem operacyjnym.

``InfrastructureException`` dziedziczy po ``TransientInfrastructureError``
(z warstwy aplikacji), co pozwala Use Case'om i taskom Celery
łapać je na poziomie ``ApplicationException`` bez importowania
infrastruktury (AUDYT-119).
"""

from application.exceptions import TransientInfrastructureError


class InfrastructureException(TransientInfrastructureError):
    """Bazowy wyjątek dla wszystkich błędów w infrastrukturii."""

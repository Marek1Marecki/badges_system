"""Middleware wstrzykujący kontener DI (Composition Root) na obiekt request.

Architektura:
- ``bootstrap.container`` żyje jako Composition Root w pakiecie ``bootstrap``.
- Warstwa ``apps`` (Delivery) nie powinna importować ``bootstrap`` bezpośrednio,
  aby reguła ``importlinter`` (Delivery Layer must not depend on Infrastructure)
  nie była łamana przez zależności pośrednie.
- Ten middleware działa jako most: pośród żądań HTTP przypisuje kontener do
  ``request.app_container``, skąd widoki w ``apps`` mogą go pobrać.
"""

from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

from bootstrap.container import get_container


class ContainerMiddleware(MiddlewareMixin):
    """Dodaje ``request.app_container`` z konfigurowanym kontenerem DI."""

    def process_request(self, request: HttpRequest) -> None:
        request.app_container = get_container()

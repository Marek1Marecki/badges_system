"""Adapter pamięci podręcznej wykorzystujący mechanizmy Django.

AUDYT-114: Graceful degradation — gdy Redis niedostępny, cache nie powinien
zatrzymywać całej aplikacji. Operacje get/set/delete łapią błędy połączenia
i logują warning, zwracając wartości domyślne.
"""

import logging
from typing import Any

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from application.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


class DjangoCacheAdapter(CachePort):
    """Implementuje CachePort używając globalnego bufora Django."""

    def set(self, key: str, value: Any, timeout_seconds: int) -> None:
        """Zapisuje wartość w cache. Ignoruje błędy połączenia (degrade gracefully)."""
        try:
            cache.set(key, value, timeout=timeout_seconds)
        except (ConnectionError, TimeoutError, ImproperlyConfigured) as exc:
            logger.warning("DjangoCacheAdapter.set failed for key %r: %s", key, exc)

    def get(self, key: str) -> Any | None:
        """Odczytuje wartość z cache. Zwraca None przy błędzie połączenia (cache miss)."""
        try:
            return cache.get(key)
        except (ConnectionError, TimeoutError, ImproperlyConfigured) as exc:
            logger.warning("DjangoCacheAdapter.get failed for key %r: %s", key, exc)
            return None

    def delete(self, key: str) -> None:
        """Usuwa wartość z cache. Ignoruje błędy połączenia."""
        try:
            cache.delete(key)
        except (ConnectionError, TimeoutError, ImproperlyConfigured) as exc:
            logger.warning("DjangoCacheAdapter.delete failed for key %r: %s", key, exc)

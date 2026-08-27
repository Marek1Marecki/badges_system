"""Adapter pamięci podręcznej wykorzystujący mechanizmy Django."""

from typing import Any

from django.core.cache import cache

from application.ports.cache_port import CachePort


class DjangoCacheAdapter(CachePort):
    """Implementuje CachePort używając globalnego bufora Django."""

    def set(self, key: str, value: Any, timeout_seconds: int) -> None:
        """Zapisuje wartość w cache."""
        cache.set(key, value, timeout=timeout_seconds)

    def get(self, key: str) -> Any | None:
        """Odczytuje wartość z cache."""
        return cache.get(key)

    def delete(self, key: str) -> None:
        """Usuwa wartość z cache."""
        cache.delete(key)

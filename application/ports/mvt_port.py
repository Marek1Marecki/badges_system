"""Port dla repozytorium kafelków wektorowych (MVT).

Zgodnie z ADR-013, warstwa aplikacyjna definiuje tylko interfejs wejściowy.
"""

from typing import Protocol


class MvtRepositoryPort(Protocol):
    """Interfejs odpytywania bazy o binarne kafelki wektorowe PBF."""

    def get_tile(self, layer_name: str, table_name: str, z: int, x: int, y: int) -> bytes | None:
        """Zwraca binarne dane kafelka MVT lub None, jeśli pusty."""
        ...

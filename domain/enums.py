"""Centralne, typowane klasy Enum dla statusów biznesowych.

AUDYT-136: Eliminacja "Magic Strings" — single source of truth
dla statusów w całej Czystej Domenie i Use Case'ach.

Klasy `StrEnum` (Python 3.11+) zapewniają, że:
- ``DomainStatus.COMPLETED == "COMPLETED"`` → True (string equality)
- Mypy wykryje literówki na etapie kompilacji
- Modele Django (`apps/tourists/models.py`) korzystają z tych samych Enumów jako `choices`

Zgodnie z ADR-021: Domena nie zna infrastruktury — te Enumy nie importują Django.
"""

from enum import StrEnum


class DomainStatus(StrEnum):
    """Status domenowy postępu w odznance (Czysta Domena).

    Chronologiczna ścieżka: NOT_STARTED → IN_PROGRESS → COMPLETED.
    COMPLETED jest nieodwracalne (Grandfather Clause — AUDYT-106/132).
    """

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class LogisticStatus(StrEnum):
    """Status logistyczny — ścieżka wysyłki do albumu (Use Case orchestration).

    Graf przejść (z `AdvanceLogisticStatusUseCase`):
    WAITING_FOR_SEND → WAITING_FOR_VERIFICATION → WAITING_FOR_RECEIVING → ALBUM
    """

    WAITING_FOR_SEND = "WAITING_FOR_SEND"
    WAITING_FOR_VERIFICATION = "WAITING_FOR_VERIFICATION"
    WAITING_FOR_RECEIVING = "WAITING_FOR_RECEIVING"
    ALBUM = "ALBUM"

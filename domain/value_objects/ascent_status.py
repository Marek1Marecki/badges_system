"""Value Object: status pojedynczego wejścia (Ascent) w kontekście wersji odznaki.

AUDYT-099: Transparentny raport "Wejść Odrzuconych" (Opcja C — Grandfather's Bin).

Dzięki ``AscentStatus`` Czysta Domena nie tylko liczy ważne wejścia,
ale także audytuje każde wejście turysty pod kątem tego,
czy "przeszło przez Sito" (pool_peaks) czy nie.

``object_id`` i ``ascent_date`` pozwalają UI pokazać turystowi,
że wejście na konkretną górę w konkretnym dniu nadal istnieje
w jego "Dzienniku Podróży", choć nie przynosi już punktów
w obecnie zdobywanej wersji regulaminu.
"""

from dataclasses import dataclass
from datetime import date

from domain.enums import AscentLifecycle


@dataclass(frozen=True)
class AscentStatus:
    """Status jednego wejścia w kontekście ewaluacji wersji odznaki.

    - ``object_id``: ID obiektu turystycznego (np. Rysy == 15).
    - ``ascent_date``: data fizycznego wejścia (pamiątka historyczna).
    - ``lifecycle``: ACTIVE / ORPHANED / EXHAUSTED (patrz AscentLifecycle).
    - ``points``: liczba przyznanych punktów (0 dla ORPHANED).
    """

    object_id: int
    ascent_date: date
    lifecycle: AscentLifecycle
    points: int

"""Modele Django (Active Record) dla infrastruktury odznak.

Ten pakiet zastępuje dawniego monolitycznego ``models.py`` (827 linii).
Każdy podzespół modeli zamieszczony jest w osobnym module w celu zwiększenia
czytelności i upraszczania konserwacji (AUDYT-128).

Wszystkie klasy pochodzą z podmodułów są ponownie wyeksportowane w
``__init__.py``, dzię czemu istniejące ``from apps.badges.models import X``
importy pozostają kompatybilne.
"""

from apps.badges.models.badge import (
    BadgeModel,
    BadgeTierModel,
    BadgeVersionModel,
    LevelType,
)
from apps.badges.models.news import (
    BadgeNewsItem,
    NewsChangeType,
)
from apps.badges.models.organizer import OrganizerModel
from apps.badges.models.osm import (
    OsmSyncConflict,
    OsmTypeMapping,
    SyncConflictStatus,
    TouristObject,
    TouristObjectStatus,
)
from apps.badges.models.proximity import (
    ProximityCandidate,
    ProximityStatus,
)
from apps.badges.models.read_model import ObjectRegionCache
from apps.badges.models.region import (
    LtreeField,
    RegionFlatModel,
    RegionLevel,
)

__all__ = [
    "BadgeModel",
    "BadgeNewsItem",
    "BadgeTierModel",
    "BadgeVersionModel",
    "LevelType",
    "LtreeField",
    "NewsChangeType",
    "ObjectRegionCache",
    "OrganizerModel",
    "OsmSyncConflict",
    "OsmTypeMapping",
    "ProximityCandidate",
    "ProximityStatus",
    "RegionFlatModel",
    "RegionLevel",
    "SyncConflictStatus",
    "TouristObject",
    "TouristObjectStatus",
]

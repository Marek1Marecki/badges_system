"""Panel administracyjny Django dla systemu odznak.

Zamieniony z monolitycznego `admin.py` (1103 linie) na pakiet z podmodułami
(AUDYT-129). Każdy podmoduł importuje odpowiednie klasy i rejestruje je
w `admin.site` poprzez dekoratory `@admin.register`.

Importowanie wszystkich podmodułów w `__init__.py` zapewnia, że Django
natychmiast widzi wszystkie rejestracje po załadowaniu pakietu.

Wszystkie klasy pochodzące z podmodułów są ponownie wyeksportowane,
dzię czemu istniejące ``from apps.badges.admin import X`` importy
pozostają kompatybilne.
"""

from apps.badges.admin.badge_admin import BadgeAdmin, BadgeVersionAdmin
from apps.badges.admin.celery_admin import (
    UnfoldClockedScheduleAdmin,
    UnfoldCrontabScheduleAdmin,
    UnfoldIntervalScheduleAdmin,
    UnfoldPeriodicTaskAdmin,
    UnfoldSolarScheduleAdmin,
)
from apps.badges.admin.filters import (
    PeakInBadgeFilter,
    PendingMappingFilter,
    RegionLevelFilter,
    ResolutionDirectionFilter,
)
from apps.badges.admin.forms import AddToBadgeForm, BadgeTierInlineFormSet
from apps.badges.admin.inlines import BadgeTierInline, ObjectRegionCacheInline
from apps.badges.admin.news_admin import BadgeNewsItemAdmin
from apps.badges.admin.organizer_admin import OrganizerAdmin
from apps.badges.admin.osm_admin import OsmTypeMappingAdmin, TouristObjectAdmin
from apps.badges.admin.proximity_admin import ProximityCandidateAdmin
from apps.badges.admin.region_admin import (
    CountryAdmin,
    MacroregionAdmin,
    MesoregionAdmin,
    ProvinceAdmin,
    ReadOnlyMapAdmin,
    SubprovinceAdmin,
    TouristRegionAdmin,
    VoivodeshipAdmin,
)
from apps.badges.admin.sync_conflict_admin import OsmSyncConflictAdmin

# Re-export key models that were previously accessible directly from
# apps.badges.admin (backward compatibility for tests / patches).
from apps.badges.models import ObjectRegionCache

__all__ = [
    "AddToBadgeForm",
    "BadgeAdmin",
    "BadgeNewsItemAdmin",
    "BadgeTierInline",
    "BadgeTierInlineFormSet",
    "BadgeVersionAdmin",
    "CountryAdmin",
    "MacroregionAdmin",
    "MesoregionAdmin",
    "ObjectRegionCacheInline",
    "OrganizerAdmin",
    "OsmSyncConflictAdmin",
    "OsmTypeMappingAdmin",
    "ObjectRegionCache",
    "PeakInBadgeFilter",
    "PendingMappingFilter",
    "ProximityCandidateAdmin",
    "ProvinceAdmin",
    "ReadOnlyMapAdmin",
    "RegionLevelFilter",
    "ResolutionDirectionFilter",
    "SubprovinceAdmin",
    "TouristObjectAdmin",
    "TouristRegionAdmin",
    "UnfoldClockedScheduleAdmin",
    "UnfoldCrontabScheduleAdmin",
    "UnfoldIntervalScheduleAdmin",
    "UnfoldPeriodicTaskAdmin",
    "UnfoldSolarScheduleAdmin",
    "VoivodeshipAdmin",
]

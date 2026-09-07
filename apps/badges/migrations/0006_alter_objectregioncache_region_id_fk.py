"""Migracja ObjectRegionCache.region_id: BigIntegerField → ForeignKey na RegionFlatModel (ADR-028).

ETL mapuje istniejące cache (przechowujące region_id jako int odpowiadający PK
staremu modelowi) na nowy schema. Zgodnie z mapowaniem z migracji 0004:

  - COUNTRY → CountryModel (pk)
  - VOIVODESHIP → VoivodeshipModel
  - PROVINCE → ProvinceModel
  - SUBPROVINCE → SubprovinceModel
  - MACROREGION → MacroregionModel
  - MESOREGION → MesoregionModel

Wszystkie te modele mają te same PK w RegionFlatModel (ETL 0004 kopiował 1:1).

Używamy SeparateDatabaseAndState, bo:
  - W DB: kolumna `region_id` już istnieje jako BigInteger — musimy najpierw
    ETL (usunięcie orphaned), potem AlterField na istniejącej kolumnie, co
    przekształca ją w FK bez change kolumny.
  - W State (Python): pole `region_id` zamieniamy na `region` (ForeignKey) —
    Django zarządza kolumną `region_id` jako FK automatycznie.
"""

import django.db.models.deletion
from django.db import migrations, models


def remove_orphaned_cache(apps, schema_editor):
    """Usuwa cache, których region_id nie istnieje w RegionFlatModel (dla NOT NULL FK)."""
    ObjectRegionCache = apps.get_model("badges", "ObjectRegionCache")
    RegionFlatModel = apps.get_model("badges", "RegionFlatModel")

    existing_flat_pks = set(RegionFlatModel.objects.values_list("pk", flat=True))
    orphaned = ObjectRegionCache.objects.exclude(region_id__in=existing_flat_pks)
    count = orphaned.count()
    orphaned.delete()
    if count:
        print(f"  {count} orphaned cache records deleted (referenced stale region PKs)")


# State change: usuwamy stary region_id, dodajemy nowy region (FK) + meta
state_operations = [
    migrations.RemoveField(
        model_name="objectregioncache",
        name="region_id",
    ),
    migrations.AddField(
        model_name="objectregioncache",
        name="region",
        field=models.ForeignKey(
            db_column="region_id",
            help_text="Region z regions_flat (ADR-028).",
            on_delete=django.db.models.deletion.CASCADE,
            related_name="cached_objects",
            to="badges.regionflatmodel",
        ),
    ),
    migrations.AlterUniqueTogether(
        name="objectregioncache",
        unique_together={("tourist_object", "region_level", "region")},
    ),
    migrations.RemoveIndex(
        model_name="objectregioncache",
        name="odznaki_obj_region__f5a923_idx",
    ),
    migrations.AddIndex(
        model_name="objectregioncache",
        index=models.Index(fields=["region_level", "region"], name="odznaki_obj_region__f5a923_idx"),
    ),
]

# DB change: ETL + ALTER COLUMN region_id na FK (kolumna już istnieje)
database_operations = [
    migrations.RunPython(remove_orphaned_cache, reverse_code=migrations.RunPython.noop),
    migrations.AlterField(
        model_name="objectregioncache",
        name="region_id",
        field=models.ForeignKey(
            db_column="region_id",
            help_text="Region z regions_flat (ADR-028).",
            on_delete=django.db.models.deletion.CASCADE,
            related_name="cached_objects",
            to="badges.regionflatmodel",
        ),
    ),
]


class Migration(migrations.Migration):
    dependencies = [
        ("badges", "0005_migrate_region_neighbors_m2m"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations,
            database_operations=database_operations,
        ),
    ]

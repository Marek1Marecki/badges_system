"""Migracja relacji M2M z TouristRegionModel do RegionFlatModel.neighbors (ADR-028).

ETL kopiuje relacje Many-to-Many ze starych pól M2M (voivodeships, macroregions,
mesoregions na TouristRegionModel) do płaskiego pola `neighbors` na
RegionFlatModel. Relacja jest dwukierunkowa — sąsiad dodany w obu kierunkach.

Operacja jest ADDITIVE — nie usuwa starych tabel.
"""

from django.db import migrations


def migrate_tourist_region_neighbors(apps, schema_editor):
    """Kopiuje M2M z starych pól TouristRegionModel do RegionFlatModel.neighbors."""
    RegionFlatModel = apps.get_model("badges", "RegionFlatModel")
    TouristRegionModel = apps.get_model("badges", "TouristRegionModel")

    pk_to_flat = {}
    for rf in RegionFlatModel.objects.all():
        pk_to_flat[rf.id] = rf

    for tr in TouristRegionModel.objects.all():
        flat_tr = pk_to_flat.get(tr.pk)
        if flat_tr is None:
            continue

        related_pk_ids = set()
        for v in tr.voivodeships.all():
            related_pk_ids.add(v.pk)
        for m in tr.macroregions.all():
            related_pk_ids.add(m.pk)
        for me in tr.mesoregions.all():
            related_pk_ids.add(me.pk)

        for related_pk in related_pk_ids:
            flat_related = pk_to_flat.get(related_pk)
            if flat_related is not None:
                flat_tr.neighbors.add(flat_related)
                flat_related.neighbors.add(flat_tr)


class Migration(migrations.Migration):
    dependencies = [
        ("badges", "0004_create_regions_flat_ltree"),
    ]

    operations = [
        migrations.RunPython(migrate_tourist_region_neighbors, reverse_code=migrations.RunPython.noop),
    ]

"""Drop historycznych tabel regionów — ADR-028 (Phase 2 cleanup).

Usuwa 7 historycznych tabel regionów:
  odznaki_country, odznaki_voivodeship, odznaki_province,
  odznaki_subprovince, odznaki_macroregion, odznaki_mesoregion,
  odznaki_tourist_region

Modele zostały usunięte z kodu (apps/badges/models/region.py),
bo zostały zastąpione przez RegionFlatModel w tabeli `regions_flat`.
ETL danych do regions_flat odbył się w migracjach 0004 + 0005.
ObjectRegionCache.region_id już wskazuje na regions_flat (migracja 0006).

Operacja jest destrukcyjna — DROP TABLE CASCADE (usuwa FK i M2M through tables).
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("badges", "0006_alter_objectregioncache_region_id_fk"),
    ]

    operations = [
        migrations.DeleteModel(
            name="CountryModel",
        ),
        migrations.DeleteModel(
            name="VoivodeshipModel",
        ),
        migrations.DeleteModel(
            name="ProvinceModel",
        ),
        migrations.DeleteModel(
            name="SubprovinceModel",
        ),
        migrations.DeleteModel(
            name="MacroregionModel",
        ),
        migrations.DeleteModel(
            name="MesoregionModel",
        ),
        migrations.DeleteModel(
            name="TouristRegionModel",
        ),
    ]

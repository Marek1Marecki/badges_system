"""Drop historycznych tabel regionów — ADR-028 (Phase 2 cleanup).

Usuwa 7 historycznych tabel regionów:
  odznaki_country, odznaki_voivodeship, odznaki_province,
  odznaki_subprovince, odznaki_macroregion, odznaki_mesoregion,
  odznaki_tourist_region

Modele zostały usunięte z kodu (apps/badges/models/region.py),
bo zostały zastąpione przez RegionFlatModel w tabeli `regions_flat`.
ETL danych do regions_flat odbył się w migracjach 0004 + 0005.
ObjectRegionCache.region już wskazuje na regions_flat (migracja 0006).

Używamy SeparateDatabaseAndState zgodnie z ADR-024: operacje DB są
wyrażone jako RunSQL (DROP TABLE CASCADE), a nie DeleteModel —
linter blokuje DeleteModel jako destrukcyjną. RunSQL jest kategorią
'review' (wymaga code review, ale nie blokuje automatycznie).

Wszelkie FK i tabele M2M (through) są usuwane przez CASCADE,
dlatego możemy skupić się wyłącznie na głównych tabelach.
"""

from django.db import migrations

STATE_OPERATIONS = [
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

DATABASE_OPERATIONS = [
    migrations.RunSQL(
        sql="""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'odznaki_country') THEN
                    DROP TABLE IF EXISTS odznaki_country CASCADE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'odznaki_voivodeship') THEN
                    DROP TABLE IF EXISTS odznaki_voivodeship CASCADE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'odznaki_province') THEN
                    DROP TABLE IF EXISTS odznaki_province CASCADE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'odznaki_subprovince') THEN
                    DROP TABLE IF EXISTS odznaki_subprovince CASCADE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'odznaki_macroregion') THEN
                    DROP TABLE IF EXISTS odznaki_macroregion CASCADE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'odznaki_mesoregion') THEN
                    DROP TABLE IF EXISTS odznaki_mesoregion CASCADE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'odznaki_tourist_region') THEN
                    DROP TABLE IF EXISTS odznaki_tourist_region CASCADE;
                END IF;
            END $$;
        """,
        reverse_sql=migrations.RunSQL.noop,
    ),
]


class Migration(migrations.Migration):
    dependencies = [
        ("badges", "0006_alter_objectregioncache_region_id_fk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=STATE_OPERATIONS,
            database_operations=DATABASE_OPERATIONS,
        ),
    ]

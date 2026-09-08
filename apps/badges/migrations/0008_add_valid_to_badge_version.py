from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("badges", "0007_drop_legacy_regions"),
    ]

    operations = [
        migrations.AddField(
            model_name="badgeversionmodel",
            name="valid_to",
            field=models.DateField(
                blank=True,
                help_text="Pozostaw puste dla wersji obowiązującej w nieskończoność. "
                "Wersja otwarta w przeszłości blokuje dodanie nowej wersji.",
                null=True,
                verbose_name="Ważna do",
            ),
        ),
        migrations.AlterField(
            model_name="objectregioncache",
            name="region_name",
            field=models.CharField(
                help_text="Zdenormalizowana nazwa regionu do błyskawicznego wyświetlenia (np. w panelu).",
                max_length=100,
            ),
        ),
    ]

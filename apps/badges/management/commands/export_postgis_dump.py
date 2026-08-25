"""Tworzy binarny dump PostgreSQL (pg_dump -Fc) z bieżącej bazy referencyjnej."""

import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """"""

    help = "Tworzy binarny dump PostgreSQL (pg_dump -Fc) z bieżącej bazy referencyjnej."

    def handle(self, *args, **options):
        """

        Args:
          *args:
          **options:

        Returns:

        """
        output_dir = Path(settings.BASE_DIR) / "data" / "reference"
        output_dir.mkdir(parents=True, exist_ok=True)
        dump_path = output_dir / "postgis_dump.custom"
        db = settings.DATABASES["default"]
        env = os.environ.copy()
        env["PGPASSWORD"] = db.get("PASSWORD", "")
        cmd = [
            "pg_dump",
            "-Fc",
            "-U",
            db.get("USER", "postgres"),
            "-h",
            db.get("HOST", "localhost"),
            "-p",
            str(db.get("PORT", 5432)),
            "-d",
            db.get("NAME", "postgres"),
            "-f",
            str(dump_path),
        ]
        self.stdout.write(self.style.WARNING(f"Tworzę dump PostgreSQL: {' '.join(cmd)}"))
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)  # noqa: S603
        if result.returncode != 0:
            self.stderr.write(self.style.ERROR(f"pg_dump failed: {result.stderr}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS(f"✅ Dump zapisany: {dump_path}"))

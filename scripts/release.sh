#!/bin/bash
set -e

echo "=== ROZPOCZYNANIE ZADAŃ WDORŻENIOWYCH (RELEASE JOB) ==="
echo "Wykonywanie migracji bazy danych..."
python manage.py migrate --noinput

echo "Zbieranie plików statycznych (collectstatic)..."
python manage.py collectstatic --noinput --clear
echo "=== ZADANIA ZAKOŃCZONE ==="
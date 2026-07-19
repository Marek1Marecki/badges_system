#!/bin/bash
set -e

# ==============================================================================
# dev-reset.sh — DESTRUKCYJNE: usuwa wolumeny DEV i odbudowuje środowisko
#
# Jedyne miejsce w całym projekcie, gdzie pojawia się `docker compose down -v`.
# Wymaga wpisania z klawiatury dokładnego słowa potwierdzającego — zwykłe
# [y/N] jest zbyt łatwe do przypadkowego przeklikania (np. wciśnięcie Enter
# z domyślnie zaznaczonym "y" w skrypcie CI albo w pośpiechu).
#
# AUTOMATYCZNY BACKUP przed usunięciem — dodane po incydencie: pierwsza
# wersja tego skryptu tylko SUGEROWAŁA backup w komunikacie, nie wykonywała
# go. To nie wystarczyło — łatwo przeoczyć sugestię w pośpiechu. Teraz
# backup jest domyślny (Y), a pominięcie wymaga świadomej odpowiedzi "n".
# ==============================================================================

echo "UWAGA: ta operacja USUNIE WSZYSTKIE DANE w wolumenach DEV"
echo "(postgis_data, redis_data) - baze, wgrane dane referencyjne, wszystko."
echo ""

read -r -p "Wykonac backup przed resetem? [T/n]: " do_backup
if [ "$do_backup" != "n" ] && [ "$do_backup" != "N" ]; then
    ./scripts/dev-backup.sh
    echo ""
fi

read -r -p "Wpisz dokladnie 'usun-dane-dev' aby potwierdzic USUNIECIE: " confirm

if [ "$confirm" != "usun-dane-dev" ]; then
    echo "Anulowano - zadne dane nie zostaly usuniete."
    exit 1
fi

echo ""
echo "Potwierdzono. Usuwanie kontenerow i wolumenow..."
docker compose down -v

echo "Odbudowywanie srodowiska od zera (schemat + puste tabele)..."
./scripts/dev-up.sh

echo ""
echo "=================================================================="
echo "UWAGA: baza ma teraz PUSTY schemat - bez danych referencyjnych"
echo "(odznak, obiektow turystycznych, regionow). To oczekiwane: reset"
echo "usuwa tez dane referencyjne, nie tylko dane uzytkownika (ADR-020 -"
echo "restore_reference_data nigdy nie jest wywolywane automatycznie)."
echo ""
echo "Aby odtworzyc dane referencyjne z zatwierdzonego snapshotu:"
echo "  docker compose exec web ./scripts/bootstrap.sh <snapshot_id>"
echo ""
echo "Aby zamiast tego przywrocic PELEN wczesniejszy stan (razem z danymi"
echo "uzytkownika) z backupu wykonanego przed chwila:"
echo "  ./scripts/dev-restore.sh ./backups/<nazwa_pliku>.dump"
echo "=================================================================="

"""Skrypt analityczny: Generowanie interaktywnego grafu powiązań (Odznaki <-> Obiekty).

Zgodnie z zasadą z SCRIPTS.md, jest to skrypt w pełni odizolowany od runtime'u, generujący plik HTML do ręcznego
podglądu w przeglądarce. Wykorzystuje bibliotekę pyvis.
"""

import os
import sys
from typing import Any

# =====================================================================
# INICJALIZACJA DJANGO (Wymagane przed importem modeli)
# =====================================================================
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()


def generate_graph() -> None:
    """Buduje graf dwudzielny, analizując popularność węzłów i generując plik HTML."""
    from collections import defaultdict

    from pyvis.network import Network

    from apps.badges.models import BadgeVersionModel

    print("Rozpoczynam analizę powiązań bazy danych...")

    # 1. Konfiguracja płótna dla grafu (Ciemny motyw, pełny ekran)
    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#1e293b",
        font_color="white",
        select_menu=True,  # Pozwala wybierać węzły z listy
        filter_menu=True,  # Pozwala filtrować np. po nazwie
    )

    # 2. Pobieramy wszystkie Wersje Odznak, które posiadają w ogóle jakąś pulę szczytów
    versions = BadgeVersionModel.objects.select_related("badge").prefetch_related("pool_peaks").all()

    badge_nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    peak_badge_count: dict[int, int] = defaultdict(int)
    peak_objects: dict[int, Any] = {}

    # Analiza danych i liczenie wystąpień
    for version in versions:
        peaks = version.pool_peaks.all()
        if not peaks:
            continue

        badge_code = version.badge.code
        badge_name = version.badge.name
        badge_id = f"badge_{badge_code}"

        # Rejestrujemy Odznakę
        if badge_id not in badge_nodes:
            net.add_node(
                badge_id,
                label=badge_code,
                title=f"ODZNAKA: {badge_name}",
                shape="hexagon",
                color="#0ea5e9",
                size=40,
                font={"color": "white", "size": 20, "face": "monospace"},
            )
            badge_nodes.add(badge_id)

        # Rejestrujemy krawędzie (powiązania) i liczymy popularność szczytów
        for peak in peaks:
            peak_badge_count[peak.id] += 1
            peak_objects[peak.id] = peak
            edges.append((badge_id, f"peak_{peak.id}"))

    print(f"Znaleziono {len(badge_nodes)} odznak i {len(peak_objects)} unikalnych obiektów.")

    # 3. Generowanie węzłów dla Szczytów (Z dynamicznym rozmiarem i kolorem!)
    for pk_id, count in peak_badge_count.items():
        peak = peak_objects[pk_id]
        node_id = f"peak_{pk_id}"

        # Matematyka wizualna (Większy obiekt = ważniejszy obiekt)
        size = 10 + (count * 6)

        if count == 1:
            color = "#22c55e"  # Zielony (Unikalny, występuje raz)
        elif count <= 3:
            color = "#eab308"  # Żółty (Popularny)
        else:
            color = "#ef4444"  # Czerwony (Przeeksploatowany / Jądro systemu)

        title_html = f"OBIEKT: {peak.name}\nTyp: {peak.type}\nWystępuje w {count} odznakach!"

        net.add_node(
            node_id,
            label=peak.name,
            title=title_html,
            shape="dot",
            color=color,
            size=size,
        )

    # 4. Łączenie Odznak ze Szczytami
    for source, target in edges:
        net.add_edge(source, target, color="#475569", width=1)

    # 5. Silnik Fizyczny (Optymalizacja grawitacji, by graf ładnie się rozłożył)
    net.force_atlas_2based(
        gravity=-50, central_gravity=0.01, spring_length=150, spring_strength=0.08, damping=0.4, overlap=0
    )

    # Dodajemy panel kontrolny dla użytkownika (by mógł sam wyłączać grawitację)
    net.show_buttons(filter_=["physics"])

    # 6. Zapis
    output_filename = "galaktyka_odznak.html"
    net.save_graph(output_filename)
    print(f"\n✅ SUKCES! Plik {output_filename} został wygenerowany w katalogu głównym projektu.")
    print("Kliknij na niego dwukrotnie, by otworzyć go w przeglądarce!")


if __name__ == "__main__":
    generate_graph()

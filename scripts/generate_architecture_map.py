"""Skrypt analityczny: Żywa Mapa Architektury (Architecture Graph).

Skanuje pliki projektu (AST), analizuje kierunki importów pomiędzy modułami i wizualizuje je za pomocą pyvis. Oznacza na
czerwono importy łamiące zasady Architektury Heksagonalnej (zdefiniowane w MODULES.md).
"""

import ast
import os
from pathlib import Path

from pyvis.network import Network

# Główne warstwy naszego systemu
ROOT_PACKAGES = {"domain", "application", "infrastructure", "apps", "bootstrap"}

LAYER_COLORS = {
    "domain": "#22c55e",  # Zielony (Czysty rdzeń)
    "application": "#3b82f6",  # Niebieski (Orkiestracja)
    "infrastructure": "#f59e0b",  # Pomarańczowy (Adaptery i baza)
    "apps": "#8b5cf6",  # Fioletowy (Django / UI)
    "bootstrap": "#ec4899",  # Różowy (DI Container)
}


def get_layer(module_name: str) -> str:
    """Zwraca główną warstwę dla danego modułu.

    Args:
      module_name: str:
      module_name: str:

    Returns:
    """
    base = module_name.split(".")[0]
    return base if base in ROOT_PACKAGES else "unknown"


def is_illegal_import(source_layer: str, target_layer: str) -> bool:
    """Implementacja twardych kontraktów z MODULES.md.

    Args:
      source_layer: str:
      target_layer: str:
      source_layer: str:
      target_layer: str:

    Returns:
    """
    if source_layer == target_layer:
        return False
    if target_layer == "unknown":
        return False  # Ignorujemy biblioteki stdlib lub 3rd party (np. django)

    # Reguły Czystej Architektury
    if source_layer == "domain":
        return True  # Domena nie może importować NICZEGO z zewnętrznych warstw!

    if source_layer == "application":
        return target_layer not in ["domain"]  # Aplikacja może tylko z domeny

    if source_layer == "infrastructure":
        # Infra MUSI znać 'apps' (bo tam są modele ORM Django) oraz 'domain' i 'application'
        return target_layer not in ["domain", "application", "apps"]

    if source_layer == "apps":
        # Widoki i Taski Celery mogą korzystać z kontenera DI, DTOsów i infrastruktury
        return target_layer not in ["bootstrap", "application", "domain", "infrastructure"]

    return False


def extract_imports(filepath: Path) -> list[str]:
    """Przeszukuje plik .py w poszukiwaniu importów za pomocą AST.

    Args:
      filepath: Path:
      filepath: Path:

    Returns:
    """
    imports = []
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    except Exception as e:
        print(f"⚠️ Pominięto plik {filepath} podczas analizy AST: {e}")
    return imports


def generate_architecture_map() -> None:
    """"""
    print("Skanowanie drzewa plików projektu...")
    project_root = Path(__file__).resolve().parent.parent

    nodes = set()
    edges = []

    # Skanowanie plików
    for layer in ROOT_PACKAGES:
        layer_path = project_root / layer
        if not layer_path.exists():
            continue

        for filepath in layer_path.rglob("*.py"):
            # Ignorujemy migracje, testy i pliki init
            if "migrations" in filepath.parts or "tests" in filepath.parts or filepath.name == "__init__.py":
                continue

            # Zamiana ścieżki na nazwę modułu (np. application.use_cases.log_ascent)
            rel_path = filepath.relative_to(project_root)
            module_name = str(rel_path).replace(".py", "").replace(os.sep, ".")
            source_layer = get_layer(module_name)

            nodes.add(module_name)

            imported_modules = extract_imports(filepath)
            for imp in imported_modules:
                target_layer = get_layer(imp)

                # Interesują nas tylko relacje wewnątrz naszego systemu
                if target_layer in ROOT_PACKAGES:
                    nodes.add(imp)
                    edges.append((module_name, imp, source_layer, target_layer))

    print(f"Znaleziono {len(nodes)} modułów oraz {len(edges)} powiązań wewnętrznych.")

    # Budowa Grafu
    net = Network(height="100vh", width="100%", bgcolor="#0f172a", font_color="white", directed=True)

    # 1. Dodawanie Węzłów
    for node in nodes:
        layer = get_layer(node)
        color = LAYER_COLORS.get(layer, "#94a3b8")

        # Ekstrakcja samej nazwy pliku do wyświetlenia (żeby nie pisać długich ścieżek)
        short_label = node.split(".")[-1]

        net.add_node(node, label=short_label, title=node, color=color, shape="dot", size=20)

    # 2. Dodawanie Krawędzi (Strzałek)
    illegal_count = 0
    for source, target, src_layer, tgt_layer in edges:
        illegal = is_illegal_import(src_layer, tgt_layer)
        if illegal:
            # CZERWONY ALARM DLA ZŁYCH IMPORTÓW
            net.add_edge(source, target, color="#ef4444", width=3, title="NIELEGALNY IMPORT!")
            illegal_count += 1
        else:
            # Standardowa strzałka w kolorze modułu źródłowego
            net.add_edge(source, target, color=LAYER_COLORS.get(src_layer), width=1, opacity=0.4)

    # 3. Silnik fizyczny
    net.force_atlas_2based(
        gravity=-80, central_gravity=0.01, spring_length=200, spring_strength=0.05, damping=0.4, overlap=0
    )

    output_filename = "architektura_systemu.html"
    net.save_graph(output_filename)

    print(f"✅ Wygenerowano mapę: {output_filename}")
    if illegal_count > 0:
        print(f"⚠️ UWAGA! Wykryto {illegal_count} powiązań łamiących czystą architekturę (czerwone linie)!")


if __name__ == "__main__":
    generate_architecture_map()

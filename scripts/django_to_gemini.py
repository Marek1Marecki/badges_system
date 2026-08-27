"""Konwerter kontekstu Django do formatu Gemini."""

import os
from pathlib import Path


def is_ignored(name: str, ignore_exact: set, ignore_ext: set) -> bool:
    """Szybkie sprawdzanie po nazwie lub rozszerzeniu.

    Args:
      name: str:
      ignore_exact: set:
      ignore_ext: set:
      name: str:
      ignore_exact: set:
      ignore_ext: set:

    Returns:
    """
    if name in ignore_exact:
        return True
    if any(name.endswith(ext) for ext in ignore_ext):
        return True
    return False


def generate_repo_summary(root_dir: str, output_file: str) -> None:
    """

    Args:
      root_dir: str:
      output_file: str:
      root_dir: str:
      output_file: str:

    Returns:

    """
    root = Path(root_dir).resolve()

    # 1. Twarde katalogi/pliki do wykluczenia (dokładna nazwa)
    ignore_exact = {
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "migrations",
        "staticfiles",
        "media",
        "data",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "db.sqlite3",
        ".DS_Store",
        "uv.lock",
    }

    # 2. Rozszerzenia do wykluczenia
    ignore_ext = {".pyc", ".pyo", ".pyd", ".gz", ".zip", ".pdf", ".png", ".jpg", ".ico"}

    # 3. Dozwolone rozszerzenia i konkretne pliki (Złoty zestaw dla AI)
    allowed_extensions = {".py", ".html", ".js", ".css", ".md", ".yml", ".yaml", ".sh"}
    allowed_files = {"Dockerfile", "pyproject.toml", ".env.example", "Makefile"}

    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"=== STRUKTURA PROJEKTU: {root.name} ===\n\n")

        # Fazowy zrzut drzewa - z optymalizacją os.walk
        for current_root, dirs, files in os.walk(root):
            # Tniemy os.walk w locie: usuwamy ignorowane katalogi, by do nich nie wchodził!
            dirs[:] = [d for d in dirs if not is_ignored(d, ignore_exact, ignore_ext)]

            current_path = Path(current_root)
            level = len(current_path.relative_to(root).parts)
            indent = " " * 4 * level

            # Nie drukujemy pustych nagłówków dla korzenia projektu
            if current_path != root:
                out.write(f"{indent}[D] {current_path.name}/\n")

            sub_indent = " " * 4 * (level + 1)
            for f in sorted(files):
                if is_ignored(f, ignore_exact, ignore_ext):
                    continue

                f_path = current_path / f
                if f_path.suffix in allowed_extensions or f in allowed_files:
                    out.write(f"{sub_indent}[F] {f}\n")

        out.write("\n" + "=" * 50 + "\n\n")
        out.write("=== ZAWARTOŚĆ PLIKÓW ===\n\n")

        # Faza 2: Zrzut treści
        for current_root, dirs, files in os.walk(root):
            # Tniemy ponowinie dla szybkości
            dirs[:] = [d for d in dirs if not is_ignored(d, ignore_exact, ignore_ext)]

            current_path = Path(current_root)
            for f in sorted(files):
                if is_ignored(f, ignore_exact, ignore_ext):
                    continue

                f_path = current_path / f
                if f_path.suffix in allowed_extensions or f in allowed_files:
                    rel_path = f_path.relative_to(root)

                    # Standardowy, zrozumiały dla AI format blokowy
                    out.write(f"--- START OF FILE {rel_path} ---\n")
                    try:
                        with open(f_path, encoding="utf-8") as file_content:
                            out.write(file_content.read())
                            # Zabezpieczenie przed brakiem nowej linii na końcu pliku
                            out.write("\n")
                    except Exception as e:
                        out.write(f"[BŁĄD ODCZYTU PLIKU: {e}]\n")
                    out.write(f"--- END OF FILE {rel_path} ---\n\n")

    print(f"Sukces! Wygenerowano plik: {output_file}")


if __name__ == "__main__":
    generate_repo_summary(".", "projekt_kontekst_gemini.txt")

"""Narzędzie do szacowania kosztów tokenów w modelach LLM."""

import sys
from pathlib import Path


def estimate_tokens(text: str) -> dict[str, int]:
    """Szacuje ilość tokenów używając darmowych heurystyk.

    Args:
      text: str:
      text: str:

    Returns:
    """
    characters = len(text)
    # Rozbijamy po białych znakach (w tym spacjach, enterach i znakach tabulacji)
    words = len(text.split())

    # 1. Metoda znakowa (z reguły ~3.5 znaku na token w kodzie programistycznym)
    tokens_by_chars = int(characters / 3.5)

    # 2. Metoda słowna (ok. 1.3 tokena na słowo / element w kodzie)
    tokens_by_words = int(words * 1.3)

    # Bierzemy średnią dla najbezpieczniejszego oszacowania
    average_tokens = (tokens_by_chars + tokens_by_words) // 2

    return {"chars": characters, "words": words, "tokens": average_tokens}


def analyze_file(filepath: str) -> None:
    """

    Args:
      filepath: str:
      filepath: str:

    Returns:

    """
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Plik {filepath} nie istnieje!")
        sys.exit(1)

    print(f"📊 Analiza pliku: {path.name}")
    print("-" * 50)

    with open(path, encoding="utf-8") as file:
        content = file.read()

    stats = estimate_tokens(content)

    # Rysowanie raportu
    print(f"Liczba znaków: {stats['chars']:,}".replace(",", " "))
    print(f"Liczba słów:   {stats['words']:,}".replace(",", " "))
    print(f"\n👉 Szacowana liczba tokenów: ~ {stats['tokens']:,}".replace(",", " "))

    # Progi bezpieczeństwa
    print("\n--- Analiza pojemności ---")
    if stats["tokens"] < 100_000:
        print("✅ BEZPIECZNIE: Wejdzie gładko w każde okno (Claude 3, GPT-4o, Gemini).")
    elif stats["tokens"] < 200_000:
        print("⚠️ OSTRZEŻENIE: Zbliżasz się do limitu Claude 3 (200k) i GPT-4 (128k).")
    elif stats["tokens"] < 1_000_000:
        print(
            "🔥 OGROMNY KONTEKST: Plik obsłuży tylko Gemini 1.5 Pro / Flash (do 1-2M tokenów) lub Claude 3.5 z podniesionym limitem."
        )
    else:
        print("💀 KATASTROFA: Przekroczono 1 milion tokenów. Prawdopodobnie wciągnąłeś katalog venv lub media!")


if __name__ == "__main__":
    # Możesz podać nazwę pliku jako argument, lub użyje domyślnej
    target_file = sys.argv[1] if len(sys.argv) > 1 else "projekt_kontekst_gemini.txt"
    analyze_file(target_file)

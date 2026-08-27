#!/usr/bin/env python3
"""Create a new ADR with proper ADR-NNN numbering and update the index."""

import re
import sys
from datetime import date
from pathlib import Path

ADRS_DIR = Path("docs/adrs")
TEMPLATE = Path("docs/adrs/ADR-TEMPLATE.md")
INDEX = Path("docs/architecture/decisions/README.md")


def next_adr_number() -> int:
    """Zwraca numer kolejnego ADR."""
    existing = []
    for f in ADRS_DIR.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d+)", f.name)
        if m:
            existing.append(int(m.group(1)))
    return max(existing, default=0) + 1


def create_adr(title: str) -> Path:
    """Tworzy nowy plik ADR z szablonu."""
    number = next_adr_number()
    filename = f"ADR-{number:03d} — {title}.md"
    filepath = ADRS_DIR / filename

    if filepath.exists():
        print(f"Error: {filepath} already exists")
        sys.exit(1)

    template = TEMPLATE.read_text(encoding="utf-8")
    today = date.today().isoformat()
    content = template.replace("[NUMER]", f"{number:03d}").replace("[Tytuł Decyzji]", title)
    content = re.sub(
        r"^> \*\*Status:\*\* `.*`$",
        "> **Status:** `proposed`",
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r"^> \*\*Data:\*\* .*$",
        f"> **Data:** {today}",
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r"^> \*\*Autor:\*\* .*$",
        "> **Autor:** [Imię i Nazwisko / AI Architect]",
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r"^> \*\*Zastępuje:\*\* .*$",
        "> **Zastępuje:** Brak",
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r"^> \*\*Zastąpiony przez:\*\* .*$",
        "> **Zastąpiony przez:** Brak",
        content,
        flags=re.MULTILINE,
    )

    filepath.write_text(content, encoding="utf-8")
    print(f"Created: {filepath}")
    return filepath


def main() -> None:
    """Główna funkcja skryptu."""
    if len(sys.argv) < 2:
        print("Usage: make adr TITLE='Your ADR title'")
        sys.exit(1)

    title = " ".join(sys.argv[1:])
    if not title:
        print("Error: Title cannot be empty")
        sys.exit(1)

    ADRS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = create_adr(title)
    print("\nNext steps:")
    print(f"  1. Edit {filepath}")
    print("  2. Fill in all sections")
    print(f"  3. Update {INDEX} with the new ADR")
    print(f"  4. Commit with message: 'feat(adr): ADR-{next_adr_number() - 1:03d} — {title}'")


if __name__ == "__main__":
    main()

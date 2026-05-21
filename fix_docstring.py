#!/usr/bin/env python3


def add_docstring():
    file_path = "domain/rules/badge_rules.py"

    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Find the validate method line (around line 271)
    for i, line in enumerate(lines):
        if "def validate(self, ascents: list[Ascent]) -> list[str]:" in line:
            # Insert docstring after the method definition
            docstring = '''        """Validate ascents for required badge rule.
        
        This rule requires verification of tourist's badge history, which is not
        available at ascent validation level. Returns empty list to allow parallel
        peak collection. Badge possession verification occurs at award level.
        
        Args:
            ascents: List of ascents to validate
            
        Returns:
            Empty list (no validation errors at this level)
        """
'''
            lines.insert(i + 1, docstring)
            break

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("Docstring added successfully!")


if __name__ == "__main__":
    add_docstring()

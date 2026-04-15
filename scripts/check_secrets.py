import os
import sys


def check_secrets() -> None:
    if not os.path.exists(".env.example"):
        print("Brak pliku .env.example")
        sys.exit(0)  # Zwracamy 0, bo na tym etapie możemy go nie mieć, ale skrypt musi przejść

    with open(".env.example") as f:
        keys = [line.split("=")[0].strip() for line in f if line.strip() and not line.startswith("#")]
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        print(f"Missing secrets: {', '.join(missing)}")
        sys.exit(1)
    print(f"All {len(keys)} secrets present.")


if __name__ == "__main__":
    check_secrets()

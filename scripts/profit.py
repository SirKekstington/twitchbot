#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path

# ============================================
# CONFIG
# ============================================

# Dein bestehendes Script
UPDATE_SCRIPT = Path("albion/killboard.py")

# Die Datei mit den Daten
PROFIT_FILE = Path("albion/killboard_store.txt")


# ============================================
# HELPER
# ============================================


def parse_profit_file() -> dict[str, int]:

    result = {"EstProfitToday": 0, "LostToday": 0}

    if not PROFIT_FILE.exists():
        return result

    with PROFIT_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            try:
                result[key] = int(value)
            except ValueError:
                pass

    return result


def format_silver(value: int) -> str:

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}b"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}m"

    if value >= 1_000:
        return f"{value / 1_000:.1f}k"

    return str(value)


# ============================================
# MAIN
# ============================================


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument("--user", required=False)

    parser.parse_args()

    # ----------------------------------------
    # UPDATE SCRIPT AUSFÜHREN
    # ----------------------------------------

    if UPDATE_SCRIPT.exists():
        try:
            subprocess.run(
                ["python", str(UPDATE_SCRIPT)],
                timeout=30,
                check=False,
                capture_output=True,
                text=True,
            )

        except Exception as exc:
            print(f"Update script failed: {exc}")
            return

    # ----------------------------------------
    # PROFIT FILE EINLESEN
    # ----------------------------------------

    data = parse_profit_file()

    profit = data.get("EstProfitToday", 0)

    lost = data.get("LostToday", 0)

    # ----------------------------------------
    # RESPONSE
    # ----------------------------------------

    profit_text = format_silver(profit)
    lost_text = format_silver(lost)

    print(f"Heutiger Profit: +{profit_text} | Verloren: -{lost_text}")


if __name__ == "__main__":
    main()

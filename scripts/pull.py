#!/usr/bin/env python3

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

ENTER_FILE = Path("data/enter_list.txt")
WINNER_FILE = Path("pull/winner.json")


def load_entries() -> list[str]:
    if not ENTER_FILE.exists():
        return []

    with ENTER_FILE.open("r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def write_winner(winner: str, pulled_by: str, total_entries: int) -> None:
    WINNER_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "winner": winner,
        "pulled_by": pulled_by,
        "total_entries": total_entries,
        "timestamp": datetime.now().strftime("%d.%m.%y %H:%M:%S"),
        "nonce": random.randint(100000, 999999),
    }

    with WINNER_FILE.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)

    args = parser.parse_args()

    entries = load_entries()

    if not entries:
        return

    winner = random.choice(entries)

    write_winner(winner=winner, pulled_by=args.user, total_entries=len(entries))

    print(f"The Winner is: @{winner}")


if __name__ == "__main__":
    main()

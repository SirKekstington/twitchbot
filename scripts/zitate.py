#!/usr/bin/env python3

import argparse
import random
from datetime import datetime
from pathlib import Path

QUOTE_FILE = Path("data/quotes.txt")


def load_quotes() -> list[str]:
    if not QUOTE_FILE.exists():
        return []

    with QUOTE_FILE.open("r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def save_quote(message: str) -> None:
    short_date = datetime.now().strftime("%d.%m.%y")

    with QUOTE_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{short_date}] {message}\n")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--user", required=True)
    parser.add_argument("--message", default="")

    args = parser.parse_args()

    message = args.message.strip()

    if message:
        save_quote(message)
        print(f'Zitat gespeichert: "{message}"')
        return

    quotes = load_quotes()

    if not quotes:
        print("Noch keine Zitate gespeichert.")
        return

    print(random.choice(quotes))


if __name__ == "__main__":
    main()

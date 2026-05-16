#!/usr/bin/env python3

import argparse
from datetime import datetime
from pathlib import Path

ENTER_FILE = Path("data/enter_list.txt")


def load_users() -> set[str]:
    if not ENTER_FILE.exists():
        return set()

    with ENTER_FILE.open("r", encoding="utf-8") as fh:
        return {line.strip().lower() for line in fh if line.strip()}


def add_user(username: str) -> bool:
    username_clean = username.strip()

    if not username_clean:
        return False

    users = load_users()

    if username_clean.lower() in users:
        return False

    with ENTER_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"{username_clean}\n")

    return True


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--user", required=True)

    args = parser.parse_args()

    username = args.user.strip()
    added = add_user(username)

    if added:
        print(f"{username} ist jetzt eingetragen.")
    else:
        print(f"{username} ist bereits eingetragen.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import argparse
import re
from datetime import datetime
from pathlib import Path

import requests

URL = "https://killboard-1.com/eu/player/MrKekstein"
STORE_FILE = Path("killboard_store.txt")


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (KillboardProfitBot/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        "Connection": "close",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20,
    )

    response.raise_for_status()
    return response.text


def extract_value(html: str, label: str) -> str:
    pattern = re.compile(
        re.escape(label) + r"[\s\S]{0,300}?(\d[\d.,]*\s*[km]?)",
        re.IGNORECASE,
    )

    match = pattern.search(html)

    if not match:
        return "0"

    return match.group(1).strip().replace(" ", "")


def parse_number(value: str) -> float:
    if not value:
        return 0.0

    value = value.strip().lower().replace(",", ".")

    multiplier = 1.0

    if value.endswith("k"):
        multiplier = 1_000.0
        value = value[:-1]

    elif value.endswith("m"):
        multiplier = 1_000_000.0
        value = value[:-1]

    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)

    if not match:
        return 0.0

    return float(match.group(0)) * multiplier


def load_store(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}

    if not path.exists():
        return data

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()

    return data


def save_store(path: Path, data: dict[str, str]) -> None:
    lines = [f"{key}={data[key]}" for key in sorted(data.keys())]

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def build_data(html: str) -> dict[str, str]:
    return {
        "EstProfitToday": extract_value(html, "Est. Profit Today"),
        "LostToday": extract_value(html, "Lost Today"),
        "UpdatedAt": datetime.now().strftime("%d.%m.%y %H:%M:%S"),
    }


def format_chat_value(value: str) -> str:
    number = parse_number(value)

    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}b"

    if number >= 1_000_000:
        return f"{number / 1_000_000:.2f}m"

    if number >= 1_000:
        return f"{number / 1_000:.1f}k"

    return str(int(number))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=False)
    parser.parse_args()

    try:
        html = fetch_html(URL)
        new_data = build_data(html)

        old_data = load_store(STORE_FILE)
        old_data.update(new_data)
        save_store(STORE_FILE, old_data)

        profit = new_data.get("EstProfitToday", "0")
        lost = new_data.get("LostToday", "0")

        profit_text = format_chat_value(profit)
        lost_text = format_chat_value(lost)

        print(f"Albion heute: Profit +{profit_text} | Lost -{lost_text}")

    except Exception as exc:
        print(f"Profit konnte nicht geladen werden: {exc}")


if __name__ == "__main__":
    main()

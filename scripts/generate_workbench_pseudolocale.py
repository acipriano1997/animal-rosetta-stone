"""Deterministic presentation-only expansion; never reads scientific data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

# Language names stay readable so the selector always offers an escape to English.
STABLE_LABELS = frozenset({"locale.english", "locale.pseudo"})


def pseudo(text: str) -> str:
    accents = str.maketrans("aAeEiIoOuUcCnN", "àÀëËïÏøØüÜçÇñÑ")
    # Placeholders are copied, never transformed; values are substituted later.
    parts = re.split(r"(\{[a-zA-Z_]+\})", text)
    expanded = "".join(part if part.startswith("{") else part.translate(accents) for part in parts)
    return "⟦" + expanded + " · " + "延" * max(3, len(text) // 3) + "⟧"


def generate(source: dict[str, str]) -> str:
    return json.dumps(
        {key: value if key in STABLE_LABELS else pseudo(value) for key, value in source.items()},
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in test catalog differs; write nothing.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "src/ars_workbench/static/locales"
    source = json.loads((root / "en.json").read_text(encoding="utf-8"))
    expected = generate(source).encode("utf-8")
    target = root / "en-XA.json"
    if args.check:
        if not target.is_file() or target.read_bytes() != expected:
            parser.exit(1, "en-XA is stale; run python scripts/generate_workbench_pseudolocale.py\n")
        print("en-XA matches deterministic English-source generation (testing only).")
    else:
        target.write_bytes(expected)


if __name__ == "__main__":
    main()

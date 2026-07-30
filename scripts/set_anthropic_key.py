"""Read the Anthropic key from the macOS clipboard and write it into .env.

Usage:
  1. Go to https://console.anthropic.com/settings/keys and create a new key.
  2. In the "new key" modal, click the copy button.
  3. Come back to the terminal and run: python scripts/set_anthropic_key.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def main() -> int:
    try:
        raw = subprocess.check_output(["pbpaste"]).decode()
    except Exception as e:
        print(f"FAIL: could not read clipboard ({e})")
        return 1

    key = raw.strip()

    if not key:
        print("FAIL: clipboard is empty. Copy the key from the Anthropic modal, then re-run.")
        return 1

    if not key.startswith("sk-ant-"):
        preview = key[:30] + ("..." if len(key) > 30 else "")
        print(f"FAIL: clipboard is not an Anthropic key.\n       Starts with: {preview!r}")
        print("Hint: after copying the key from Anthropic, don't copy anything else — "
              "just run 'python scripts/set_anthropic_key.py' directly.")
        return 1

    non_ascii = [(i, c) for i, c in enumerate(key) if ord(c) > 127]
    if non_ascii:
        print(f"FAIL: non-ASCII characters in key at positions {[i for i,_ in non_ascii]}")
        return 1

    if "\n" in key or " " in key:
        print("FAIL: key contains whitespace inside it — clipboard may have extra content.")
        return 1

    if ENV.exists():
        content = ENV.read_text()
    else:
        content = ""

    if "ANTHROPIC_API_KEY=" in content:
        content = re.sub(
            r"^ANTHROPIC_API_KEY=.*$",
            f"ANTHROPIC_API_KEY={key}",
            content,
            flags=re.M,
        )
    else:
        content = f"ANTHROPIC_API_KEY={key}\n" + content

    ENV.write_text(content)
    print(f"OK: wrote key of length {len(key)} to {ENV.name}")
    print("Next: run 'python scripts/check.py'")
    return 0


if __name__ == "__main__":
    sys.exit(main())

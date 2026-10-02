    #!/usr/bin/env python3
"""Load clearly marked demo employees into the local database.

Usage (from project root):
  .venv\\Scripts\\python scripts\\load_demo.py          # Windows
  .venv/bin/python scripts/load_demo.py               # macOS/Linux

  Add --force to insert even if employees already exist.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.demo_data import load_demo_data  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Load RedmondHR demo data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Insert demo rows even if the database already has employees",
    )
    args = parser.parse_args()
    n = load_demo_data(force=args.force)
    if n == 0:
        print("No demo data inserted (database already has employees). Use --force to add anyway.")
    else:
        print(f"Inserted {n} demo employee(s). Names are prefixed with [DEMO].")


if __name__ == "__main__":
    main()

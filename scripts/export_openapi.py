#!/usr/bin/env python3
"""Dump FastAPI OpenAPI JSON. Do not edit the output by hand — run scripts/gen-api.sh."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_IMPORT = "api.main:app"
OUT = ROOT / "contracts" / "api" / "openapi.json"


def main() -> None:
    sys.path.insert(0, str(ROOT))
    mod_name, _, attr = APP_IMPORT.partition(":")
    app = getattr(importlib.import_module(mod_name), attr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()

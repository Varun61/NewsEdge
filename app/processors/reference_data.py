"""Loader for externalised reference lists (data/reference/*.json).

Curated domain lists (institutional bellwethers, marquee buyers, promoter/PE
sellers, high-pledge watchlist, F&O universe, FDA firm→symbol map) used to be
hardcoded across the intelligence modules. They now live as editable JSON under
``data/reference/`` so they can be tuned without code changes.

Every loader takes the previous in-code list as a ``default`` fallback, so a
missing or malformed data file degrades gracefully to prior behaviour rather
than silently emptying a gate.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List

logger = logging.getLogger("newsedge.processors.reference_data")

_DIR = Path(__file__).resolve().parents[2] / "data" / "reference"


@lru_cache(maxsize=None)
def _load_raw(name: str):
    fp = _DIR / f"{name}.json"
    try:
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Reference data '%s' failed to load (%s); using in-code default.", name, exc)
    return None


def load_set(name: str, default: Iterable[str], upper: bool = True) -> set[str]:
    data = _load_raw(name)
    if isinstance(data, list) and data:
        return {(s.upper() if upper else s) for s in data if isinstance(s, str)}
    return {(s.upper() if upper else s) for s in default}


def load_list(name: str, default: Iterable[str]) -> List[str]:
    data = _load_raw(name)
    if isinstance(data, list) and data:
        return [s for s in data if isinstance(s, str)]
    return list(default)


def load_dict(name: str, default: Dict) -> Dict:
    data = _load_raw(name)
    if isinstance(data, dict) and data:
        return data
    return dict(default)

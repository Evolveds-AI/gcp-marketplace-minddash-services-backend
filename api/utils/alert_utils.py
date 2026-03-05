from __future__ import annotations

from typing import List


def normalize_frequency(value: str) -> str:
    v = (value or "").strip().lower()
    # Normalizaciones simples; dejar abierto para extender
    aliases = {
        "diario": "diario",
        "daily": "diario",
        "semanal": "semanal",
        "weekly": "semanal",
        "mensual": "mensual",
        "monthly": "mensual",
    }
    return aliases.get(v, value)


def unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result

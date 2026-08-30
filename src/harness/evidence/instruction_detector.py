"""Deterministic instruction-pattern detector (T049, FR-027, research R6)."""

from __future__ import annotations

import json
import re
from typing import Any

# Heuristic patterns for instructions aimed at the agent inside evidence.
_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|your)\s+(instructions|policy|policies|rules)", re.I),
    re.compile(r"you\s+are\s+now\s+(an?\s+)?(unrestricted|jailbroken|developer)", re.I),
    re.compile(r"(send|upload|exfiltrate|post)\s+(all\s+)?(the\s+)?(data|evidence|files|report)s?\s+to\s+\S+", re.I),
    re.compile(r"execute\s+(the\s+)?command", re.I),
    re.compile(r"(curl|wget)\s+\S+\s*\|\s*(sh|bash)", re.I),
    re.compile(r"reveal\s+(any\s+)?(passwords?|secrets?|api\s*keys?|tokens?|credentials?)", re.I),
    re.compile(r"(grant|give)\s+(yourself|me|the\s+agent)\s+(additional\s+)?(permissions?|access|privileges?)", re.I),
    re.compile(r"(disable|delete|modify|suppress)\s+(the\s+)?audit", re.I),
    re.compile(r"(use|select|invoke)\s+(the\s+)?(unapproved|unregistered|new)\s+tool", re.I),
    re.compile(r"remember\s+this\s+(instruction|rule)\s+for\s+(all\s+)?future", re.I),
    re.compile(r"system\s*prompt\s*[:>]", re.I),
    re.compile(r"isolate\s+(the\s+)?endpoint|disable\s+(the\s+)?account|block\s+(the\s+)?ip", re.I),
]


def detect_instructions(content: Any) -> list[str]:
    """Return matched pattern descriptions found in the content (empty = clean)."""
    text = content if isinstance(content, str) else json.dumps(content, default=str)
    return [p.pattern for p in _PATTERNS if p.search(text)]

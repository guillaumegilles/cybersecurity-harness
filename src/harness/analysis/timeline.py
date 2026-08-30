"""Deterministic timeline builder (T026, FR-013)."""

from __future__ import annotations

from harness.storage.models import EvidenceItem, TimelineEvent
from harness.storage.repositories import CaseScopedRepository


def build_timeline(repo: CaseScopedRepository) -> list[TimelineEvent]:
    """Order evidence by event timestamp deterministically (Constitution V)."""
    items = [e for e in repo.list(EvidenceItem) if e.event_at is not None]
    items.sort(key=lambda e: (e.event_at, e.id))
    events: list[TimelineEvent] = []
    for item in items:
        etype = item.content.get("event_type") or item.content.get("rule_name") or "observation"
        desc_bits = [f"[{item.source}]", str(etype)]
        raw = item.content.get("raw", {})
        if isinstance(raw, dict):
            for key in ("host", "user", "process", "dest_ip", "location", "recipient"):
                if key in raw:
                    desc_bits.append(f"{key}={raw[key]}")
        ev = TimelineEvent(
            case_id=repo.ctx.case_id,
            event_at=item.event_at,
            description=" ".join(desc_bits),
            evidence_ids=[item.id],
        )
        repo.add(ev)
        events.append(ev)
    repo.session.flush()
    return events

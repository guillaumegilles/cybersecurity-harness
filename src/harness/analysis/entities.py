"""Deterministic affected-entity extraction (T026, FR-014)."""

from __future__ import annotations

import re

from harness.storage.models import AffectedEntity, EvidenceItem
from harness.storage.repositories import CaseScopedRepository

_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# Field-name -> entity type mapping.
_FIELD_TYPES = {
    "user": "user", "recipient": "user", "owner": "user", "user_id": "user",
    "host": "endpoint", "endpoint": "endpoint", "hostname": "endpoint", "asset_id": "endpoint",
    "process": "process", "parent": "process", "parent_process": "process",
    "dest_ip": "ip_address", "ip": "ip_address", "src_ip": "ip_address",
    "path": "file", "file_opened": "file",
    "app": "application", "client": "application",
}


def extract_entities(repo: CaseScopedRepository) -> list[AffectedEntity]:
    seen: dict[tuple[str, str], set[str]] = {}
    for item in repo.list(EvidenceItem):
        raw = item.content.get("raw", item.content)
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            if not isinstance(value, str) or not value:
                continue
            etype = _FIELD_TYPES.get(key)
            if etype is None:
                continue
            if etype == "ip_address" and not _IP_RE.match(value):
                continue
            seen.setdefault((etype, value), set()).add(item.id)

    entities: list[AffectedEntity] = []
    for (etype, identifier), evidence_ids in sorted(seen.items()):
        ent = AffectedEntity(
            case_id=repo.ctx.case_id,
            entity_type=etype,
            identifier=identifier,
            evidence_ids=sorted(evidence_ids),
        )
        repo.add(ent)
        entities.append(ent)
    repo.session.flush()
    return entities

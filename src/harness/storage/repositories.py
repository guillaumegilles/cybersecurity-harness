"""Case-scoped repository layer (FR-003, research R12).

Every read/write requires an explicit CaseContext; queries are always
filtered by case_id, making cross-case reads structurally impossible
through this API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from harness.storage import models as m

T = TypeVar("T")


class CaseIsolationError(Exception):
    """Raised when an operation would cross case boundaries."""


@dataclass(frozen=True)
class CaseContext:
    case_id: str
    analyst_id: str
    agent_execution_id: str


_CASE_SCOPED = (
    m.EvidenceItem,
    m.Claim,
    m.Hypothesis,
    m.AffectedEntity,
    m.TimelineEvent,
    m.InvestigationReport,
    m.ResponseActionProposal,
    m.ToolOperation,
    m.AuthorizationDecision,
    m.AnalystFeedback,
)


class CaseScopedRepository:
    """All access to case-scoped entities goes through this class."""

    def __init__(self, session: Session, ctx: CaseContext) -> None:
        self._session = session
        self._ctx = ctx

    @property
    def ctx(self) -> CaseContext:
        return self._ctx

    @property
    def session(self) -> Session:
        return self._session

    def add(self, obj: object) -> object:
        case_id = getattr(obj, "case_id", None)
        if case_id is None:
            raise CaseIsolationError("object lacks case_id; cannot persist through case-scoped repo")
        if case_id != self._ctx.case_id:
            raise CaseIsolationError(
                f"attempted write to case {case_id} from context {self._ctx.case_id}"
            )
        self._session.add(obj)
        return obj

    def list(self, model: Type[T]) -> Sequence[T]:
        if model not in _CASE_SCOPED:
            raise CaseIsolationError(f"{model.__name__} is not case-scoped accessible")
        stmt = select(model).where(model.case_id == self._ctx.case_id)  # type: ignore[attr-defined]
        return self._session.scalars(stmt).all()

    def get(self, model: Type[T], obj_id: str) -> T | None:
        if model not in _CASE_SCOPED:
            raise CaseIsolationError(f"{model.__name__} is not case-scoped accessible")
        stmt = select(model).where(
            model.id == obj_id,  # type: ignore[attr-defined]
            model.case_id == self._ctx.case_id,  # type: ignore[attr-defined]
        )
        return self._session.scalars(stmt).first()

    def get_claim_evidence_links(self, claim_id: str) -> Sequence[m.ClaimEvidenceLink]:
        # Verify the claim belongs to this case first (isolation).
        claim = self.get(m.Claim, claim_id)
        if claim is None:
            return []
        stmt = select(m.ClaimEvidenceLink).where(m.ClaimEvidenceLink.claim_id == claim_id)
        return self._session.scalars(stmt).all()

    def add_claim_evidence_link(self, link: m.ClaimEvidenceLink) -> m.ClaimEvidenceLink:
        claim = self.get(m.Claim, link.claim_id)
        evidence = self.get(m.EvidenceItem, link.evidence_id)
        if claim is None or evidence is None:
            raise CaseIsolationError("claim or evidence not in current case")
        self._session.add(link)
        return link

    def commit(self) -> None:
        self._session.commit()


def get_case(session: Session, case_id: str, analyst_id: str) -> m.InvestigationCase | None:
    """Case lookup honoring org policy (single-role model, clarification Q3).

    Dev/eval policy: analysts may access cases they initiated. Returns None
    (indistinguishable from nonexistent) otherwise (FR-019).
    """
    case = session.get(m.InvestigationCase, case_id)
    if case is None or case.analyst_id != analyst_id:
        return None
    return case

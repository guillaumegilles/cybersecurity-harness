"""Model gateway (T018, research R3).

Narrow interface; the model has NO tool access and NO authority — its output
is treated as untrusted hypothesis material. FakeModel provides deterministic
behavior for dev/eval; a litellm-backed implementation can be swapped in.
"""

from __future__ import annotations

import json
from typing import Protocol

from harness.config.settings import get_settings


class ModelGateway(Protocol):
    model_version: str

    def complete(self, system: str, user: str) -> str: ...


class FakeModel:
    """Deterministic model for dev/eval. Produces conservative, evidence-bound
    hypothesis JSON derived only from structural features of the input."""

    model_version = "fake-deterministic-v1"

    def complete(self, system: str, user: str) -> str:
        # Deterministic heuristic "reasoning" over the demarcated evidence blob.
        text = user.lower()
        hypotheses = []
        if "powershell" in text and ("winword" in text or "macro" in text or "docm" in text):
            hypotheses.append(
                {
                    "statement": "Malicious document spawned PowerShell (likely macro-based initial access)",
                    "evaluation": "supported",
                    "confidence": "medium",
                    "confirming_evidence_needed": "Retrieve decoded PowerShell command content and file hash reputation",
                    "rejecting_evidence_needed": "Evidence the document and command are part of a sanctioned admin workflow",
                }
            )
            hypotheses.append(
                {
                    "statement": "Legitimate administrative script executed from a document workflow",
                    "evaluation": "inconclusive",
                    "confidence": "low",
                    "confirming_evidence_needed": "Change-management record or admin confirmation for this command",
                    "rejecting_evidence_needed": "Outbound C2-like network traffic or persistence artifacts",
                }
            )
        if "impossible travel" in text or ("signin" in text and "location" in text):
            hypotheses.append(
                {
                    "statement": "Account compromise via credential theft (impossible travel)",
                    "evaluation": "inconclusive",
                    "confidence": "low",
                    "confirming_evidence_needed": "MFA prompt outcomes and device fingerprint mismatch",
                    "rejecting_evidence_needed": "VPN provider ASN explains the second location",
                }
            )
            hypotheses.append(
                {
                    "statement": "Sign-ins explained by corporate/consumer VPN egress",
                    "evaluation": "inconclusive",
                    "confidence": "low",
                    "confirming_evidence_needed": "Confirmation user was traveling or using VPN",
                    "rejecting_evidence_needed": "Concurrent interactive sessions from both locations",
                }
            )
        if not hypotheses:
            hypotheses.append(
                {
                    "statement": "Insufficient evidence to establish a specific explanation",
                    "evaluation": "inconclusive",
                    "confidence": "inconclusive",
                    "confirming_evidence_needed": "Additional related events from approved sources",
                    "rejecting_evidence_needed": "",
                }
            )
        return json.dumps({"hypotheses": hypotheses})


class LiteLLMModel:
    """Real-provider gateway; only constructed when FAKE_MODEL=false."""

    def __init__(self, model_name: str) -> None:
        self.model_version = model_name

    def complete(self, system: str, user: str) -> str:
        import litellm  # imported lazily; optional dependency

        resp = litellm.completion(
            model=self.model_version,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or "{}"


def get_model_gateway() -> ModelGateway:
    settings = get_settings()
    if settings.fake_model:
        return FakeModel()
    return LiteLLMModel(settings.model_name)

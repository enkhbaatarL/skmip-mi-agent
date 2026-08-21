from __future__ import annotations


AGENT_NAME = "parameter_agent"

MODEL_PARAMETER_PROPOSAL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "LiqUtilAdjustment",
    },
)
PROPOSAL_SCOPE_EXCLUDED_REASON_CODE = "PROPOSAL_SCOPE_EXCLUDED"

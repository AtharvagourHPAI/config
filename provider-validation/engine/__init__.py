"""Provider Contract Change Validation Engine — deterministic, explainable core.

This package contains no Streamlit (or other UI) imports. The Streamlit app and the
batch scorer both import from here.
"""

from __future__ import annotations

from .decision_engine import decide
from .enums import (
    ChangeAction,
    ChangeCategory,
    ContractStatus,
    Outcome,
    ScreeningTier,
    YesNo,
)
from .loaders import DEFAULT_WORKBOOK, IntegrityError, load_all
from .models import (
    ChangeRequest,
    Decision,
    ProviderContract,
    RuleResult,
    RuleSpec,
    TagSet,
)
from .scoring import score_all
from .tag_engine import derive

__all__ = [
    "decide",
    "derive",
    "score_all",
    "load_all",
    "DEFAULT_WORKBOOK",
    "IntegrityError",
    "Outcome",
    "ChangeAction",
    "ChangeCategory",
    "ContractStatus",
    "ScreeningTier",
    "YesNo",
    "ChangeRequest",
    "ProviderContract",
    "Decision",
    "RuleResult",
    "RuleSpec",
    "TagSet",
]

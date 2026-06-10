"""Loading and caching of the editable YAML configuration.

Keeping config access in one place means rules, the decision engine, and loaders
all read the same cached rulebook/outcome definitions, and tests can point the
engine at alternate config by passing explicit paths.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
RULES_PATH = CONFIG_DIR / "rules.yaml"
OUTCOMES_PATH = CONFIG_DIR / "outcomes.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@functools.lru_cache(maxsize=None)
def load_rules_config(path: str | None = None) -> dict[str, Any]:
    """Return the parsed ``rules.yaml`` (``rules`` + ``parameters``)."""
    return _read_yaml(Path(path) if path else RULES_PATH)


@functools.lru_cache(maxsize=None)
def load_outcomes_config(path: str | None = None) -> dict[str, Any]:
    """Return the parsed ``outcomes.yaml`` (vocabulary + default actions)."""
    return _read_yaml(Path(path) if path else OUTCOMES_PATH)


def rule_params(path: str | None = None) -> dict[str, Any]:
    """Convenience accessor for the ``parameters`` block of the rulebook."""
    return load_rules_config(path).get("parameters", {})


def default_contract_action(outcome: str, path: str | None = None) -> str:
    """Map an outcome name to its default downstream contract action."""
    actions = load_outcomes_config(path).get("default_contract_actions", {})
    return actions.get(outcome, "")

"""Prompt module governance — versioned prompt registry, drift detection, seed data.

Usage::

    from packages.agents.prompts import PromptModule, PromptRegistry
    from packages.agents.prompts.seed import create_seeded_registry
    from packages.agents.prompts.compiler import PromptCompiler, Overlay

    registry = create_seeded_registry()
    compiler = PromptCompiler(registry)
    result = compiler.compile(
        module_id="planner_v1",
        variables={"name": "Alice"},
        overlays=[Overlay(id="ov1", body="Extra section.")],
    )
"""

from packages.agents.prompts.compiler import (
    CompiledPrompt,
    DuplicateOverlayError,
    MissingVariableError,
    Overlay,
    PromptCompiler,
    SecretOverlayError,
    UnknownVariableError,
)
from packages.agents.prompts.drift import DriftReport, detect_drift, detect_drift_all
from packages.agents.prompts.registry import PromptModule, PromptRegistry

__all__ = [
    "PromptModule",
    "PromptRegistry",
    "DriftReport",
    "detect_drift",
    "detect_drift_all",
    "CompiledPrompt",
    "DuplicateOverlayError",
    "MissingVariableError",
    "Overlay",
    "PromptCompiler",
    "SecretOverlayError",
    "UnknownVariableError",
]

"""Quality gate system — 6-layer validation for oh-my-class artifacts.

Gates run sequentially. Any CRITICAL failure at any layer blocks export.
Layer thresholds are configured in gate_config.yaml.
"""

from packages.quality.calibrate import calibrate_gates

__all__ = ["calibrate_gates"]

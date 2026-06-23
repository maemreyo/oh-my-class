"""Layer 5 — Human-in-the-Loop.

LangGraph interrupt() → webhook notification → teacher approval.
Timeout: 24 hours → auto-escalate to admin.
Max revisions: 3 cycles before full replan.
"""

from packages.quality.layer5_human.interrupt_handler import InterruptHandler

__all__ = ["InterruptHandler"]

from __future__ import annotations

from dataclasses import dataclass


TERMINAL_STAGES = {"COMPLETED", "ERROR", "CANCELLED", "TIMEOUT"}


@dataclass(frozen=True)
class LifecycleDecision:
    accepted: bool
    reason_code: str


def apply_signal(*, current_stage: str, signal: str, already_requested: bool = False) -> LifecycleDecision:
    stage = current_stage.upper()
    sig = signal.lower()
    if sig == "cancel":
        if stage in TERMINAL_STAGES:
            return LifecycleDecision(False, "LIFECYCLE_TERMINAL_NOOP")
        if already_requested:
            return LifecycleDecision(False, "LIFECYCLE_CANCEL_DUPLICATE")
        return LifecycleDecision(True, "LIFECYCLE_CANCEL_ACCEPTED")
    if sig == "retry":
        if stage in {"ERROR", "CANCELLED", "TIMEOUT"}:
            return LifecycleDecision(True, "LIFECYCLE_RETRY_ACCEPTED")
        if stage in TERMINAL_STAGES:
            return LifecycleDecision(False, "LIFECYCLE_RETRY_ILLEGAL_STATE")
        return LifecycleDecision(False, "LIFECYCLE_RETRY_OUT_OF_ORDER")
    return LifecycleDecision(False, "LIFECYCLE_SIGNAL_UNSUPPORTED")

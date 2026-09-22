"""Validate the production readiness gate closure artifacts."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]


def _contains(text: str, needle: str) -> bool:
    return needle in text


def _check_file(path: Path, required_phrases: list[str], failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for phrase in required_phrases:
        if not _contains(text, phrase):
            failures.append(f"{path.relative_to(ROOT)}: missing {phrase!r}")


def main() -> int:
    failures: list[str] = []

    _check_file(
        ROOT / "docs/architecture/components/security-isolation.md",
        [
            "## 5. Production Readiness Gate (release blocker)",
            "Redaction validated:",
            "Tenant isolation validated:",
            "Policy enforcement validated:",
            "Explainability validated:",
            "Audit validated:",
            "Fail-closed validated:",
        ],
        failures,
    )
    _check_file(
        ROOT / "docs/reference/security/authz.md",
        [
            "## 9. Production readiness gate alignment",
            "security conformance suite is a release blocker",
            "redaction validated",
            "tenant isolation validated",
            "policy enforcement validated",
            "explainability validated",
            "audit validated",
            "fail-closed validated",
        ],
        failures,
    )
    _check_file(
        ROOT / "docs/architecture/components/system-api.md",
        [
            "release readiness is blocked until the production readiness gate evidence bundle validates redaction, tenant isolation, policy enforcement, explainability, audit, and fail-closed behavior.",
        ],
        failures,
    )
    _check_file(
        ROOT / "docs/architecture/components/neuro-symbolic-core.md",
        [
            "mandatory preprocessing redaction layer",
            "Explainability Required",
            "The active policy snapshot version used for scoring MUST be included in response metadata and audit logs",
            "The immutable audit trail MUST additionally capture caller identity, tenant, policy snapshot version, model version, retrieval sources, and final decision for every scoring operation.",
        ],
        failures,
    )
    _check_file(
        ROOT / "eigenos_full_system_test_checklist.sh",
        [
            "check-production-readiness-gate.py",
            "pytest -q src/services/system-api/tests/test_security_baseline.py",
            "pytest -q src/services/system-api/tests/test_validation_errors.py",
            "pytest -q src/services/system-api/tests/test_observability_smoke.py",
            "pytest -q src/services/system-api/tests/test_explain_execution_contract.py",
        ],
        failures,
    )

    if failures:
        print("[production-readiness-gate] validation failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("[production-readiness-gate] production readiness gate artifacts are complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_API_ROOT = REPO_ROOT / "src" / "services" / "system-api"
COMPILER_ROOT = REPO_ROOT / "src" / "services" / "eigen-compiler"
CLI_FIXTURES_ROOT = REPO_ROOT / "src" / "rust" / "apps" / "cli" / "tests" / "fixtures"


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _write_or_check(path: Path, payload: str, check: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == payload:
        return False
    if check:
        print(f"[needs-update] {path.relative_to(REPO_ROOT)}")
        return True
    path.write_text(payload, encoding="utf-8")
    print(f"[updated] {path.relative_to(REPO_ROOT)}")
    return True


def update_jobspec_expected(check: bool) -> bool:
    sys.path.insert(0, str(SYSTEM_API_ROOT / "src"))
    from system_api.jobspec_parser import parse_jobspec_to_submit_request

    changed = False
    positive_root = SYSTEM_API_ROOT / "tests" / "fixtures" / "jobspec" / "positive"
    for case_dir in sorted(positive_root.iterdir()):
        req = parse_jobspec_to_submit_request(case_dir / "job.yaml")
        expected = {
            "name": req.name,
            "target": req.target,
            "priority": req.priority,
            "entrypoint": req.eigen_lang.entrypoint,
            "compiler_options": dict(req.compiler_options),
            "metadata": dict(req.metadata),
            "dependencies": list(req.dependencies),
        }
        expected_path = case_dir / "expected.json"
        changed = _write_or_check(expected_path, _canonical_json(expected), check) or changed
    return changed


def update_compiler_expected(check: bool) -> bool:
    sys.path.insert(0, str(COMPILER_ROOT / "src"))
    from eigen_compiler.compiler import compile_eigen_lang
    from eigen_compiler.proto_gen import ensure_generated

    ensure_generated()

    changed = False
    golden_root = COMPILER_ROOT / "tests" / "golden"
    for case_dir in sorted(golden_root.iterdir()):
        source = (case_dir / "program.eigen.py").read_bytes()
        compiled = json.loads(compile_eigen_lang(source).aqo_json.decode("utf-8"))
        expected_path = case_dir / "expected.aqo.json"
        changed = _write_or_check(expected_path, _canonical_json(compiled), check) or changed
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Update deterministic golden fixtures for MVP-2 conformance suites.")
    parser.add_argument("--check", action="store_true", help="Check mode: do not write files, fail if any fixture is stale.")
    args = parser.parse_args()

    changed = False
    changed = update_jobspec_expected(check=args.check) or changed
    changed = update_compiler_expected(check=args.check) or changed

    cli_fixtures = sorted(CLI_FIXTURES_ROOT.glob("*.yaml"))
    print(f"[info] Verified CLI fixture set exists ({len(cli_fixtures)} files): {CLI_FIXTURES_ROOT.relative_to(REPO_ROOT)}")

    if args.check and changed:
        print("[error] Golden fixtures are out of date. Run scripts/ci/update-golden-fixtures.py and commit the changes.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?Set ROOT_DIR to the repository root, e.g. ROOT_DIR=/path/to/Eigen-OS}"
cd "$ROOT_DIR"

echo "[0] Environment"
git status --short
python3 --version
cargo --version || true
docker --version
docker compose version

echo "[1] Docker compose config + build + up"
docker compose -f deploy/docker/docker-compose.yml config
docker compose -f deploy/docker/docker-compose.yml build --no-cache
docker compose -f deploy/docker/docker-compose.yml up -d
docker compose -f deploy/docker/docker-compose.yml ps
docker compose -f deploy/docker/docker-compose.yml logs --tail=200

echo "[2] Runtime smoke"
docker compose -f deploy/docker/docker-compose.yml exec system-api sh -lc 'echo system-api OK'
docker compose -f deploy/docker/docker-compose.yml exec eigen-kernel sh -lc 'echo eigen-kernel OK'
docker compose -f deploy/docker/docker-compose.yml exec eigen-compiler sh -lc 'echo eigen-compiler OK'
docker compose -f deploy/docker/docker-compose.yml exec driver-manager sh -lc 'echo driver-manager OK'

echo "[3] Docs / repo integrity"
python3 scripts/ci/check-contract-drift.py
bash scripts/ci/check-docs-smoke.sh


echo "[4] Formatting / static checks"
bash scripts/ci/lint.sh

echo "[5] Unit tests (all services)"
bash scripts/test/run-unit-tests.sh

echo "[6] Contract compatibility suites"
bash scripts/test/run-contract-compatibility-suite.sh
bash scripts/test/run-scheduler-contract-compatibility-suite.sh

echo "[7] Phase gates"
bash scripts/ci/check-phase8a-gates.sh
bash scripts/ci/check-phase8b-gates.sh
bash scripts/ci/check-phase8c-gates.sh
bash scripts/ci/check-phase9a-gates.sh
bash scripts/ci/check-phase9b-gates.sh

echo "[8] Product 1.0 / release closure"
python3 scripts/ci/check-product-1-0-manifest.py
python3 scripts/ci/check-product-1-0-wave1-closure.py
python3 scripts/ci/check-product-1-0-wave2-planning.py
python3 scripts/ci/check-migration-notes.py || true

echo "[9] Rust workspace tests"
cd "$ROOT_DIR/src/rust"
cargo test --workspace
cd "$ROOT_DIR"

echo "[10] Service-level explicit tests worth keeping in the release run"
pytest -q src/services/system-api/tests/test_e2e_smoke_submit_watch_results.py
pytest -q src/services/system-api/tests/test_observability_smoke.py
pytest -q src/services/system-api/tests/test_security_baseline.py
pytest -q src/services/system-api/tests/test_public_error_conformance.py
pytest -q src/services/system-api/tests/test_validation_errors.py
pytest -q src/services/system-api/tests/test_public_envelope_versioning.py
pytest -q src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py
pytest -q src/services/system-api/tests/test_idempotency.py
pytest -q src/services/system-api/tests/test_stream_job_updates.py
pytest -q src/services/system-api/tests/test_qrtx_dag_and_lifecycle.py
pytest -q src/services/system-api/tests/test_kernel_delegation.py
pytest -q src/services/system-api/tests/test_lqm_atomic_offline_failover.py
pytest -q src/services/system-api/tests/test_knowledge_base_service.py
pytest -q src/services/system-api/tests/test_pattern_miner_service.py
pytest -q src/services/system-api/tests/test_qfs_blob_backends.py
pytest -q src/services/system-api/tests/test_optimizer_contract_fixture.py
pytest -q src/services/system-api/tests/test_knowledge_base_contract_fixture.py
pytest -q src/services/system-api/tests/test_learning_control_plane_contract_fixture.py
pytest -q src/services/system-api/tests/test_explain_execution_contract.py
pytest -q src/services/system-api/tests/test_batch_execution_optimizer.py
pytest -q src/services/system-api/tests/test_e2e_real_backend_execution.py
pytest -q src/services/system-api/tests/test_e2e_vqe_contract_stability.py
pytest -q src/services/driver-manager/tests/test_qdriver_v1_conformance.py
pytest -q src/services/driver-manager/tests/test_rollback_governance.py
pytest -q src/services/driver-manager/tests/test_parity_tolerance_suite.py
pytest -q src/services/driver-manager/tests/test_parity_policy_fixture.py
pytest -q src/services/driver-manager/tests/test_official_driver_matrix_fixture.py
pytest -q src/services/driver-manager/tests/test_device_profile_registry.py
pytest -q src/services/driver-manager/tests/test_registry.py
pytest -q src/services/driver-manager/tests/test_secret_lifecycle.py
pytest -q src/services/driver-manager/tests/test_grpc_skeleton.py
pytest -q src/services/driver-manager/tests/test_aws_braket_driver.py
pytest -q src/services/driver-manager/tests/test_qiskit_runtime_driver.py
pytest -q src/services/driver-manager/tests/test_simulator_driver.py
pytest -q src/services/eigen-compiler/tests/test_conformance_suite.py
pytest -q src/services/eigen-compiler/tests/test_compilation_rpc.py
pytest -q src/services/eigen-compiler/tests/test_handoff_contract.py
cd "$ROOT_DIR/src/services/benchmark-service"
PYTHONPATH=src pytest -q tests
cd "$ROOT_DIR"

echo "[11] Coverage"
bash scripts/test/generate-coverage.sh

echo "DONE"

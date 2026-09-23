//! Generic, infrastructure-owned iterative hybrid workflow orchestration.
//!
//! The engine owns the `initialize → evaluate → optimize → checkpoint →
//! converge → finalize` lifecycle.  Its evaluator is the Kernel's binding and
//! Driver Manager boundary: optimizer plugins receive observations only.

use std::collections::BTreeMap;
use std::time::Instant;

use optimizer_plugin::{InitializeInput, IterationContext, OptimizerPluginRuntime, StepInput};
use qfs::{
    CHECKPOINT_ENVELOPE_SCHEMA_VERSION, CHECKPOINT_RUNTIME_API_VERSION, CheckpointArtifactRef,
    CheckpointCompatibilityWindow, CheckpointEnvelopeV1, CheckpointExtensions,
    CheckpointGuardrails, CheckpointIntegrity, CheckpointPayloadRefs, CheckpointProvenance,
    CheckpointRestoreLineage, CheckpointRetentionPolicy, CheckpointTraceLinks, CircuitFsLocal,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ConvergencePolicy {
    pub max_iterations: u64,
    pub absolute_objective_tolerance: Option<f64>,
    pub relative_objective_tolerance: Option<f64>,
    pub parameter_tolerance: Option<f64>,
}

impl ConvergencePolicy {
    fn validate(&self) -> Result<(), WorkflowError> {
        for tolerance in [
            self.absolute_objective_tolerance,
            self.relative_objective_tolerance,
            self.parameter_tolerance,
        ] {
            if tolerance.is_some_and(|value| !value.is_finite() || value < 0.0) {
                return Err(WorkflowError::InvalidConfiguration(
                    "tolerances must be finite non-negative values",
                ));
            }
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TerminationReason {
    Converged,
    MaxIterations,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkflowPhase {
    Initialize,
    Evaluate,
    Optimize,
    Checkpoint,
    Converge,
    Finalize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvaluationRecord {
    /// Optimizer steps completed before this Driver Manager evaluation.
    pub iteration: u64,
    pub evaluation: u64,
    pub parameters: Vec<f64>,
    pub objective_value: f64,
    pub elapsed_millis: u128,
    pub optimizer_state: Vec<u8>,
    pub optimizer_metadata: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OptimizerStepRecord {
    pub iteration: u64,
    pub evaluated_parameters: Vec<f64>,
    pub objective_value: f64,
    pub next_parameters: Vec<f64>,
    pub elapsed_millis: u128,
    pub optimizer_state: Vec<u8>,
    pub optimizer_metadata: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkflowCheckpoint {
    /// Next parameters to evaluate when resumed.
    pub parameters: Vec<f64>,
    pub optimizer_state: Vec<u8>,
    pub actual_optimizer_steps: u64,
    pub actual_evaluations: u64,
    pub previous_objective: Option<f64>,
}

/// Deterministic inputs pinned to an iterative checkpoint.  These identifiers
/// and checksums intentionally exclude credentials and raw provider payloads.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowCheckpointProvenance {
    pub workflow_id: String,
    pub optimizer_plugin_id: String,
    pub optimizer_plugin_version: String,
    pub optimizer_plugin_api_version: String,
    pub seed: u64,
    pub backend: String,
    pub shots: u64,
    pub source_checksum: String,
    pub compiled_artifact_ref: String,
    pub configuration_checksum: String,
    #[serde(default)]
    pub compatibility_metadata: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct PersistedWorkflowCheckpoint {
    provenance: WorkflowCheckpointProvenance,
    checkpoint: WorkflowCheckpoint,
}

/// QFS-backed immutable checkpoint persistence for iterative workflows.
#[derive(Debug, Clone)]
pub struct WorkflowCheckpointStore {
    qfs: CircuitFsLocal,
}

impl WorkflowCheckpointStore {
    pub fn new(qfs: CircuitFsLocal) -> Self {
        Self { qfs }
    }

    pub fn persist(
        &self,
        provenance: &WorkflowCheckpointProvenance,
        checkpoint: &WorkflowCheckpoint,
    ) -> Result<String, WorkflowError> {
        validate_provenance(provenance)?;
        let iteration = checkpoint.actual_optimizer_steps;
        let base = format!(
            "qfs://jobs/{}/checkpoints/iterative/{iteration:020}",
            provenance.workflow_id
        );
        let payload_ref = format!("{base}/state.json");
        let envelope_ref = format!("{base}/envelope.json");
        let payload = serde_json::to_vec(&PersistedWorkflowCheckpoint {
            provenance: provenance.clone(),
            checkpoint: checkpoint.clone(),
        })
        .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?;
        let hash = format!("sha256:{:x}", Sha256::digest(&payload));
        let envelope = CheckpointEnvelopeV1 {
            schema_version: CHECKPOINT_ENVELOPE_SCHEMA_VERSION.into(),
            checkpoint_id: format!("{}-{iteration:020}", provenance.workflow_id),
            job_id: provenance.workflow_id.clone(),
            created_at: format!("iteration:{iteration}"),
            runtime_version: CHECKPOINT_RUNTIME_API_VERSION.into(),
            payload_refs: CheckpointPayloadRefs {
                state_segments: vec![CheckpointArtifactRef {
                    path: payload_ref.clone(),
                    content_hash: hash.clone(),
                    size_bytes: payload.len() as u64,
                }],
                memory_graph_ref: provenance.compiled_artifact_ref.clone(),
                execution_cursor_ref: payload_ref.clone(),
            },
            integrity: CheckpointIntegrity {
                checksum_set: hash,
                signature_ref: String::new(),
            },
            provenance: CheckpointProvenance {
                compiler_version: provenance.source_checksum.clone(),
                optimizer_version: provenance.optimizer_plugin_version.clone(),
                model_version: provenance.configuration_checksum.clone(),
                backend_profile: provenance.backend.clone(),
                deterministic_seed: provenance.seed,
            },
            trace_links: CheckpointTraceLinks {
                artifact_manifest_ref: provenance.compiled_artifact_ref.clone(),
                dataset_metadata_ref: format!(
                    "qfs://jobs/{}/input/source.checksum",
                    provenance.workflow_id
                ),
                checkpoint_chain_ref: format!(
                    "qfs://jobs/{}/checkpoints/iterative/",
                    provenance.workflow_id
                ),
            },
            guardrails: CheckpointGuardrails {
                declared_size_bytes: payload.len() as u64,
                estimated_restore_cost_units: 1,
                ttl_class: "workflow".into(),
            },
            compatibility: CheckpointCompatibilityWindow {
                min_reader_version: Some(CHECKPOINT_RUNTIME_API_VERSION.into()),
                max_reader_version: Some(CHECKPOINT_RUNTIME_API_VERSION.into()),
            },
            extensions: CheckpointExtensions {
                extension_keys: vec!["io.eigen.iterative-workflow/v1".into()],
            },
            retention: CheckpointRetentionPolicy::default(),
            restore_lineage: CheckpointRestoreLineage::default(),
        };
        envelope
            .validate()
            .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?;
        self.qfs
            .write_bytes(&payload_ref, &payload)
            .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?;
        self.qfs
            .write_bytes(
                &envelope_ref,
                &serde_json::to_vec(&envelope)
                    .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?,
            )
            .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?;
        Ok(envelope_ref)
    }

    /// Returns `None` only before the first completed iteration. Invalid or
    /// incompatible persisted state fails closed instead of restarting at zero.
    pub fn load_latest_compatible(
        &self,
        expected: &WorkflowCheckpointProvenance,
    ) -> Result<Option<WorkflowCheckpoint>, WorkflowError> {
        validate_provenance(expected)?;
        let prefix = format!("qfs://jobs/{}/checkpoints/iterative/", expected.workflow_id);
        let envelope_ref = match self
            .qfs
            .list_refs(&prefix)
            .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?
            .into_iter()
            .filter(|r| r.ends_with("/envelope.json"))
            .max()
        {
            Some(r) => r,
            None => return Ok(None),
        };
        let envelope: CheckpointEnvelopeV1 = serde_json::from_slice(
            &self
                .qfs
                .read_bytes(&envelope_ref)
                .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?,
        )
        .map_err(|e| WorkflowError::Checkpoint(format!("invalid checkpoint envelope: {e}")))?;
        envelope
            .validate()
            .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?;
        let payload_ref = envelope
            .payload_refs
            .state_segments
            .first()
            .ok_or_else(|| WorkflowError::Checkpoint("checkpoint has no state segment".into()))?
            .path
            .clone();
        let payload = self
            .qfs
            .read_bytes(&payload_ref)
            .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?;
        envelope
            .verify_payload_integrity(&payload)
            .map_err(|e| WorkflowError::Checkpoint(e.to_string()))?;
        let persisted: PersistedWorkflowCheckpoint = serde_json::from_slice(&payload)
            .map_err(|e| WorkflowError::Checkpoint(format!("invalid checkpoint payload: {e}")))?;
        if persisted.provenance != *expected {
            return Err(WorkflowError::Checkpoint(
                "checkpoint provenance is incompatible with this replay".into(),
            ));
        }
        Ok(Some(persisted.checkpoint))
    }
}

fn validate_provenance(value: &WorkflowCheckpointProvenance) -> Result<(), WorkflowError> {
    if [
        &value.workflow_id,
        &value.optimizer_plugin_id,
        &value.optimizer_plugin_version,
        &value.optimizer_plugin_api_version,
        &value.backend,
        &value.source_checksum,
        &value.compiled_artifact_ref,
        &value.configuration_checksum,
    ]
    .iter()
    .any(|field| field.is_empty())
    {
        return Err(WorkflowError::InvalidConfiguration(
            "checkpoint provenance fields must be non-empty",
        ));
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkflowReport {
    pub termination_reason: TerminationReason,
    pub claimed_iterations: u64,
    pub actual_optimizer_steps: u64,
    pub actual_evaluations: u64,
    pub evaluations: Vec<EvaluationRecord>,
    pub optimizer_steps: Vec<OptimizerStepRecord>,
    pub checkpoint: WorkflowCheckpoint,
    pub phases: Vec<WorkflowPhase>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkflowError {
    InvalidConfiguration(&'static str),
    Evaluator(String),
    Optimizer(String),
    Checkpoint(String),
}

impl std::fmt::Display for WorkflowError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for WorkflowError {}

/// Kernel-owned objective boundary. Implementations bind the supplied values
/// to immutable HybridWorkflow IR/AQO and execute the resulting circuit via
/// Driver Manager; they must not expose provider access to an optimizer.
pub trait ObjectiveEvaluator {
    fn evaluate(&mut self, parameters: &[f64]) -> Result<f64, WorkflowError>;
}

/// Cancellation is polled before every evaluation and optimizer step.
pub trait CancellationSignal {
    fn is_cancelled(&self) -> bool;
}

pub struct IterativeHybridWorkflowEngine<'a, E, C> {
    evaluator: E,
    cancellation: C,
    optimizer: &'a mut OptimizerPluginRuntime,
    policy: ConvergencePolicy,
    metadata: BTreeMap<String, String>,
}

impl<'a, E: ObjectiveEvaluator, C: CancellationSignal> IterativeHybridWorkflowEngine<'a, E, C> {
    pub fn new(
        evaluator: E,
        cancellation: C,
        optimizer: &'a mut OptimizerPluginRuntime,
        policy: ConvergencePolicy,
        metadata: BTreeMap<String, String>,
    ) -> Self {
        Self {
            evaluator,
            cancellation,
            optimizer,
            policy,
            metadata,
        }
    }

    pub fn run(mut self, initial_parameters: Vec<f64>) -> WorkflowReport {
        self.run_from(initial_parameters, None, None)
    }

    /// Resumes from a durable QFS checkpoint.  The checkpoint describes the
    /// next evaluation, so its counters are never fabricated or replayed.
    pub fn resume(mut self, checkpoint: WorkflowCheckpoint) -> WorkflowReport {
        self.run_from(checkpoint.parameters.clone(), Some(checkpoint), None)
    }

    /// Resumes the latest matching QFS checkpoint or starts a new workflow when
    /// no completed iteration exists. Corruption and provenance mismatch fail
    /// the workflow; neither condition may silently reinitialize an optimizer.
    pub fn run_or_resume(
        mut self,
        initial_parameters: Vec<f64>,
        store: &WorkflowCheckpointStore,
        provenance: &WorkflowCheckpointProvenance,
    ) -> WorkflowReport {
        match store.load_latest_compatible(provenance) {
            Ok(Some(checkpoint)) => self.run_from(
                checkpoint.parameters.clone(),
                Some(checkpoint),
                Some((store, provenance)),
            ),
            Ok(None) => self.run_from(initial_parameters, None, Some((store, provenance))),
            Err(error) => failed_report(initial_parameters, error.to_string()),
        }
    }

    fn run_from(
        &mut self,
        initial_parameters: Vec<f64>,
        resume: Option<WorkflowCheckpoint>,
        checkpoint_store: Option<(&WorkflowCheckpointStore, &WorkflowCheckpointProvenance)>,
    ) -> WorkflowReport {
        let mut phases = vec![WorkflowPhase::Initialize];
        let started = Instant::now();
        let mut records = Vec::new();
        let mut step_records = Vec::new();
        let (mut parameters, mut steps, mut evaluations, mut previous_objective, init_error) =
            match resume {
                Some(checkpoint) => {
                    let restored = self
                        .optimizer
                        .plugin_mut()
                        .and_then(|plugin| plugin.restore(&checkpoint.optimizer_state));
                    (
                        checkpoint.parameters,
                        checkpoint.actual_optimizer_steps,
                        checkpoint.actual_evaluations,
                        checkpoint.previous_objective,
                        restored.err().map(|error| error.to_string()),
                    )
                }
                None => {
                    let initialized = self.optimizer.plugin_mut().and_then(|plugin| {
                        plugin.initialize(InitializeInput {
                            parameters: initial_parameters.clone(),
                            metadata: self.metadata.clone(),
                        })
                    });
                    (
                        initial_parameters,
                        0,
                        0,
                        None,
                        initialized.err().map(|error| error.to_string()),
                    )
                }
            };
        let mut state = Vec::new();
        let mut reason = TerminationReason::Failed;
        let mut error = init_error;

        if error.is_none()
            && (parameters.is_empty() || parameters.iter().any(|value| !value.is_finite()))
        {
            error = Some(
                WorkflowError::InvalidConfiguration(
                    "initial parameters must be non-empty finite values",
                )
                .to_string(),
            );
        }
        if error.is_none() {
            error = self.policy.validate().err().map(|value| value.to_string());
        }

        while error.is_none() {
            if self.cancellation.is_cancelled() {
                reason = TerminationReason::Cancelled;
                break;
            }
            phases.push(WorkflowPhase::Evaluate);
            let objective = match self.evaluator.evaluate(&parameters) {
                Ok(value) if value.is_finite() => value,
                Ok(_) => {
                    error = Some("Evaluator(\"objective must be finite\")".into());
                    break;
                }
                Err(value) => {
                    error = Some(value.to_string());
                    break;
                }
            };
            evaluations += 1;
            state = match self
                .optimizer
                .plugin_mut()
                .and_then(|plugin| plugin.state())
            {
                Ok(value) => value,
                Err(value) => {
                    error = Some(value.to_string());
                    break;
                }
            };
            records.push(EvaluationRecord {
                iteration: steps,
                evaluation: evaluations,
                parameters: parameters.clone(),
                objective_value: objective,
                elapsed_millis: started.elapsed().as_millis(),
                optimizer_state: state.clone(),
                optimizer_metadata: BTreeMap::new(),
            });
            phases.push(WorkflowPhase::Converge);
            if has_converged(
                &self.policy,
                objective,
                previous_objective,
                &parameters,
                records
                    .get(records.len().saturating_sub(2))
                    .map(|r| r.parameters.as_slice()),
            ) {
                reason = TerminationReason::Converged;
                break;
            }
            if steps >= self.policy.max_iterations {
                reason = TerminationReason::MaxIterations;
                break;
            }
            if self.cancellation.is_cancelled() {
                reason = TerminationReason::Cancelled;
                break;
            }
            phases.push(WorkflowPhase::Optimize);
            let output = match self.optimizer.plugin_mut().and_then(|plugin| {
                plugin.step(StepInput {
                    parameters: parameters.clone(),
                    objective_value: objective,
                    gradient: None,
                    context: IterationContext {
                        iteration: steps,
                        max_iterations: Some(self.policy.max_iterations),
                        metadata: self.metadata.clone(),
                    },
                })
            }) {
                Ok(value) => value,
                Err(value) => {
                    error = Some(value.to_string());
                    break;
                }
            };
            if output.parameters.len() != parameters.len()
                || output.parameters.iter().any(|value| !value.is_finite())
            {
                error = Some("Optimizer(\"returned invalid parameter vector\")".into());
                break;
            }
            parameters = output.parameters;
            state = output.state;
            step_records.push(OptimizerStepRecord {
                iteration: steps,
                evaluated_parameters: records
                    .last()
                    .expect("evaluation recorded before optimization")
                    .parameters
                    .clone(),
                objective_value: objective,
                next_parameters: parameters.clone(),
                elapsed_millis: started.elapsed().as_millis(),
                optimizer_state: state.clone(),
                optimizer_metadata: output.metadata,
            });
            steps += 1;
            phases.push(WorkflowPhase::Checkpoint);
            previous_objective = Some(objective);
            if let Some((store, provenance)) = checkpoint_store {
                let checkpoint = WorkflowCheckpoint {
                    parameters: parameters.clone(),
                    optimizer_state: state.clone(),
                    actual_optimizer_steps: steps,
                    actual_evaluations: evaluations,
                    previous_objective,
                };
                if let Err(value) = store.persist(provenance, &checkpoint) {
                    error = Some(value.to_string());
                    break;
                }
        }
        if error.is_some() {
            reason = TerminationReason::Failed;
        }
        phases.push(WorkflowPhase::Finalize);
        if let Err(value) = self.optimizer.deactivate() {
            if error.is_none() {
                error = Some(value.to_string());
                reason = TerminationReason::Failed;
            }
        }
        let checkpoint = WorkflowCheckpoint {
            parameters,
            optimizer_state: state,
            actual_optimizer_steps: steps,
            actual_evaluations: evaluations,
            previous_objective,
        };
        WorkflowReport {
            termination_reason: reason,
            claimed_iterations: steps,
            actual_optimizer_steps: steps,
            actual_evaluations: evaluations,
            evaluations: records,
            optimizer_steps: step_records,
            checkpoint,
            phases,
            error,
        }
    }
}

fn failed_report(parameters: Vec<f64>, error: String) -> WorkflowReport {
    WorkflowReport {
        termination_reason: TerminationReason::Failed,
        claimed_iterations: 0,
        actual_optimizer_steps: 0,
        actual_evaluations: 0,
        evaluations: Vec::new(),
        optimizer_steps: Vec::new(),
        checkpoint: WorkflowCheckpoint {
            parameters,
            optimizer_state: Vec::new(),
            actual_optimizer_steps: 0,
            actual_evaluations: 0,
            previous_objective: None,
        },
        phases: vec![WorkflowPhase::Initialize, WorkflowPhase::Finalize],
        error: Some(error),
   
fn has_converged(
    policy: &ConvergencePolicy,
    objective: f64,
    previous: Option<f64>,
    parameters: &[f64],
    prior_parameters: Option<&[f64]>,
) -> bool {
    policy
        .absolute_objective_tolerance
        .is_some_and(|tol| objective.abs() <= tol)
        || previous.is_some_and(|prior| {
            policy
                .relative_objective_tolerance
                .is_some_and(|tol| (objective - prior).abs() <= tol * prior.abs().max(1.0))
        })
        || prior_parameters.is_some_and(|prior| {
            policy.parameter_tolerance.is_some_and(|tol| {
                parameters
                    .iter()
                    .zip(prior)
                    .all(|(current, old)| (current - old).abs() <= tol)
            })
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_plugin::CobylaPlugin;
    use std::sync::{
        Arc,

    struct NeverCancelled;
    impl CancellationSignal for NeverCancelled {
        fn is_cancelled(&self) -> bool {
            false
        }
    }
    struct Function(fn(&[f64]) -> f64);
    impl ObjectiveEvaluator for Function {
        fn evaluate(&mut self, parameters: &[f64]) -> Result<f64, WorkflowError> {
            Ok((self.0)(parameters))
        }
    }
    fn runtime() -> OptimizerPluginRuntime {
        OptimizerPluginRuntime::activate(Box::new(CobylaPlugin::default()), "optimizer", "1.0.0")
            .unwrap()
    }
    fn policy(max_iterations: u64) -> ConvergencePolicy {
        ConvergencePolicy {
            max_iterations,
            absolute_objective_tolerance: None,
            relative_objective_tolerance: None,
            parameter_tolerance: None,
        }
    }

    fn provenance() -> WorkflowCheckpointProvenance {
        WorkflowCheckpointProvenance {
            workflow_id: "iterative-resume".into(),
            optimizer_plugin_id: "io.eigen.optimizer.cobyla".into(),
            optimizer_plugin_version: "1.0.0".into(),
            optimizer_plugin_api_version: "1.0.0".into(),
            seed: 7,
            backend: "simulator".into(),
            shots: 1024,
            source_checksum: "sha256:source".into(),
            compiled_artifact_ref: "qfs://jobs/iterative-resume/compiled/circuit.aqo.json".into(),
            configuration_checksum: "sha256:config".into(),
            compatibility_metadata: BTreeMap::new(),
        }
    }

    #[test]
    fn converges_after_multiple_driver_manager_style_evaluations() {
        let mut optimizer = runtime();
        let mut config = policy(10);
        config.absolute_objective_tolerance = Some(0.01);
        let report = IterativeHybridWorkflowEngine::new(
            Function(|p| p[0] * p[0]),
            NeverCancelled,
            &mut optimizer,
            config,
            BTreeMap::new(),
        )
        .run(vec![0.2]);
        assert_eq!(report.termination_reason, TerminationReason::Converged);
        assert!(report.actual_evaluations > 1);
        assert_eq!(report.claimed_iterations, report.actual_optimizer_steps);
        assert!(report.actual_evaluations >= report.actual_optimizer_steps + 1);
    }

    #[test]
    fn reaches_max_iterations_without_inventing_counts_for_a_non_vqe_objective() {
        let mut optimizer = runtime();
        let report = IterativeHybridWorkflowEngine::new(
            Function(|p| (p[0] - 100.0).powi(2)),
            NeverCancelled,
            &mut optimizer,
            policy(3),
            BTreeMap::new(),
        )
        .run(vec![0.0]);
        assert_eq!(report.termination_reason, TerminationReason::MaxIterations);
        assert_eq!(
            (
                report.claimed_iterations,
                report.actual_optimizer_steps,
                report.actual_evaluations
            ),
            (3, 3, 4)
        );
    }

    #[test]
    fn evaluator_failure_is_terminal_and_preserves_completed_counts() {
        struct Failing;
        impl ObjectiveEvaluator for Failing {
            fn evaluate(&mut self, _: &[f64]) -> Result<f64, WorkflowError> {
                Err(WorkflowError::Evaluator(
                    "driver manager unavailable".into(),
                ))
            }
        }
        let mut optimizer = runtime();
        let report = IterativeHybridWorkflowEngine::new(
            Failing,
            NeverCancelled,
            &mut optimizer,
            policy(3),
            BTreeMap::new(),
        )
        .run(vec![1.0]);
        assert_eq!(report.termination_reason, TerminationReason::Failed);
        assert_eq!(
            (report.actual_optimizer_steps, report.actual_evaluations),
            (0, 0)
        );
        assert!(report.error.unwrap().contains("driver manager unavailable"));
    }

    #[test]
    fn qfs_checkpoint_resume_continues_at_the_next_iteration_with_identical_state() {
        struct CancelAfter(Arc<AtomicUsize>);
        impl CancellationSignal for CancelAfter {
            fn is_cancelled(&self) -> bool {
                self.0.fetch_add(1, Ordering::SeqCst) >= 2
            }
        }
        let root = tempfile::tempdir().unwrap();
        let store = WorkflowCheckpointStore::new(CircuitFsLocal::new(root.path()));
        let inputs = provenance();
        let mut interrupted_optimizer = runtime();
        let interrupted = IterativeHybridWorkflowEngine::new(
            Function(|p| (p[0] - 100.0).powi(2)),
            CancelAfter(Arc::new(AtomicUsize::new(0))),
            &mut interrupted_optimizer,
            policy(3),
            BTreeMap::new(),
        )
        .run_or_resume(vec![0.0], &store, &inputs);
        assert_eq!(interrupted.termination_reason, TerminationReason::Cancelled);
        assert_eq!(interrupted.actual_optimizer_steps, 1);

        let mut resumed_optimizer = runtime();
        let resumed = IterativeHybridWorkflowEngine::new(
            Function(|p| (p[0] - 100.0).powi(2)),
            NeverCancelled,
            &mut resumed_optimizer,
            policy(3),
            BTreeMap::new(),
        )
        .run_or_resume(vec![999.0], &store, &inputs);
        assert_eq!(resumed.termination_reason, TerminationReason::MaxIterations);
        assert_eq!(resumed.actual_optimizer_steps, 3);
        assert_eq!(resumed.actual_evaluations, 4);

        let mut uninterrupted_optimizer = runtime();
        let uninterrupted = IterativeHybridWorkflowEngine::new(
            Function(|p| (p[0] - 100.0).powi(2)),
            NeverCancelled,
            &mut uninterrupted_optimizer,
            policy(3),
            BTreeMap::new(),
        )
        .run(vec![0.0]);
        assert_eq!(resumed.checkpoint, uninterrupted.checkpoint);
    }

    #[test]
    fn incompatible_checkpoint_fails_closed_instead_of_restarting() {
        let root = tempfile::tempdir().unwrap();
        let store = WorkflowCheckpointStore::new(CircuitFsLocal::new(root.path()));
        let inputs = provenance();
        store
            .persist(
                &inputs,
                &WorkflowCheckpoint {
                    parameters: vec![1.0],
                    optimizer_state: vec![1],
                    actual_optimizer_steps: 1,
                    actual_evaluations: 1,
                    previous_objective: Some(1.0),
                },
            )
            .unwrap();
        let mut incompatible = inputs.clone();
        incompatible.backend = "other-backend".into();
        let mut optimizer = runtime();
        let report = IterativeHybridWorkflowEngine::new(
            Function(|p| p[0]),
            NeverCancelled,
            &mut optimizer,
            policy(3),
            BTreeMap::new(),
        )
        .run_or_resume(vec![0.0], &store, &incompatible);
        assert_eq!(report.termination_reason, TerminationReason::Failed);
        assert!(report.error.unwrap().contains("incompatible"));
    }
}

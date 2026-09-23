//! Generic, infrastructure-owned iterative hybrid workflow orchestration.
//!
//! The engine owns the `initialize → evaluate → optimize → checkpoint →
//! converge → finalize` lifecycle.  Its evaluator is the Kernel's binding and
//! Driver Manager boundary: optimizer plugins receive observations only.

use std::collections::BTreeMap;
use std::time::Instant;

use optimizer_plugin::{InitializeInput, IterationContext, OptimizerPluginRuntime, StepInput};
use serde::{Deserialize, Serialize};

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
        self.run_from(initial_parameters, None)
    }

    /// Resumes from a durable QFS checkpoint.  The checkpoint describes the
    /// next evaluation, so its counters are never fabricated or replayed.
    pub fn resume(mut self, checkpoint: WorkflowCheckpoint) -> WorkflowReport {
        self.run_from(checkpoint.parameters.clone(), Some(checkpoint))
    }

    fn run_from(
        &mut self,
        initial_parameters: Vec<f64>,
        resume: Option<WorkflowCheckpoint>,
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
}

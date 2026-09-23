//! Sandboxed optimizer-plugin SDK and deterministic reference implementation.
//!
//! Plugins are selected by the platform lifecycle manager; they receive only
//! objective observations and declared iteration context. They cannot execute
//! circuits, access QFS, providers, user source, filesystem, or network APIs.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const OPTIMIZER_PLUGIN_API_VERSION: &str = "1.0.0";

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InitializeInput {
    pub parameters: Vec<f64>,
    pub metadata: BTreeMap<String, String>,
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IterationContext {
    pub iteration: u64,
    pub max_iterations: Option<u64>,
    pub metadata: BTreeMap<String, String>,
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StepInput {
    pub parameters: Vec<f64>,
    pub objective_value: f64,
    pub gradient: Option<Vec<f64>>,
    pub context: IterationContext,
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StepOutput {
    pub parameters: Vec<f64>,
    pub state: Vec<u8>,
    pub metadata: BTreeMap<String, String>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OptimizerError {
    InvalidInput(&'static str),
    InvalidState,
    IncompatibleApi { required: String, actual: String },
}
impl std::fmt::Display for OptimizerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for OptimizerError {}

/// Official runtime boundary. Implementations must be activated by the plugin
/// lifecycle before this interface is reachable by a workflow engine.
pub trait OptimizerPlugin: Send {
    fn plugin_id(&self) -> &'static str;
    fn api_version(&self) -> &'static str {
        OPTIMIZER_PLUGIN_API_VERSION
    }
    fn initialize(&mut self, input: InitializeInput) -> Result<Vec<u8>, OptimizerError>;
    fn step(&mut self, input: StepInput) -> Result<StepOutput, OptimizerError>;
    fn state(&self) -> Result<Vec<u8>, OptimizerError>;
    fn restore(&mut self, state: &[u8]) -> Result<(), OptimizerError>;
    fn finalize(&mut self) -> Result<(), OptimizerError>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LifecycleState {
    Discovered,
    Validated,
    Active,
    Deactivated,
    Error,
}

/// Runtime registry populated after official discovery/validation/activation.
/// It deliberately accepts no artifact path or loader callback, preventing an
/// alternate in-process/import-based plugin loading path.
pub struct OptimizerPluginRuntime {
    state: LifecycleState,
    plugin: Box<dyn OptimizerPlugin>,
}
impl OptimizerPluginRuntime {
    pub fn activate(
        plugin: Box<dyn OptimizerPlugin>,
        manifest_type: &str,
        manifest_api_version: &str,
    ) -> Result<Self, OptimizerError> {
        if manifest_type != "optimizer" {
            return Err(OptimizerError::InvalidInput(
                "manifest plugin_type must be optimizer",
            ));
        }
        if manifest_api_version != plugin.api_version() {
            return Err(OptimizerError::IncompatibleApi {
                required: OPTIMIZER_PLUGIN_API_VERSION.into(),
                actual: manifest_api_version.into(),
            });
        }
        if plugin.api_version() != OPTIMIZER_PLUGIN_API_VERSION {
            return Err(OptimizerError::IncompatibleApi {
                required: OPTIMIZER_PLUGIN_API_VERSION.into(),
                actual: plugin.api_version().into(),
            });
        }
        Ok(Self {
            state: LifecycleState::Active,
            plugin,
        })
    }
    pub fn state(&self) -> LifecycleState {
        self.state
    }
    pub fn plugin_mut(&mut self) -> Result<&mut dyn OptimizerPlugin, OptimizerError> {
        if self.state != LifecycleState::Active {
            return Err(OptimizerError::InvalidState);
        }
        Ok(self.plugin.as_mut())
    }
    pub fn deactivate(&mut self) -> Result<(), OptimizerError> {
        self.plugin.finalize()?;
        self.state = LifecycleState::Deactivated;
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct CobylaState {
    parameters: Vec<f64>,
    best_objective: Option<f64>,
    radius: f64,
    coordinate: usize,
    direction: f64,
}
/// Deterministic derivative-free, COBYLA-compatible reference optimizer.
/// It performs coordinate trust-region polling; each response is deterministic
/// and derives its next candidate from the preceding objective evaluation.
pub struct CobylaPlugin {
    state: Option<CobylaState>,
}
impl Default for CobylaPlugin {
    fn default() -> Self {
        Self { state: None }
    }
}
impl CobylaPlugin {
    fn encode(state: &CobylaState) -> Result<Vec<u8>, OptimizerError> {
        serde_json::to_vec(state).map_err(|_| OptimizerError::InvalidState)
    }
}
impl OptimizerPlugin for CobylaPlugin {
    fn plugin_id(&self) -> &'static str {
        "io.eigen.optimizer.cobyla"
    }
    fn initialize(&mut self, input: InitializeInput) -> Result<Vec<u8>, OptimizerError> {
        if input.parameters.is_empty() || input.parameters.iter().any(|p| !p.is_finite()) {
            return Err(OptimizerError::InvalidInput(
                "parameters must be non-empty finite values",
            ));
        }
        self.state = Some(CobylaState {
            parameters: input.parameters,
            best_objective: None,
            radius: 0.1,
            coordinate: 0,
            direction: -1.0,
        });
        self.state()
    }
    fn step(&mut self, input: StepInput) -> Result<StepOutput, OptimizerError> {
        if input.parameters.is_empty()
            || !input.objective_value.is_finite()
            || input.parameters.iter().any(|p| !p.is_finite())
        {
            return Err(OptimizerError::InvalidInput(
                 "objective and parameters must be non-empty finite values",
            ));
        }
        if input.gradient.as_ref().is_some_and(|gradient| {
            gradient.len() != input.parameters.len()
                || gradient.iter().any(|value| !value.is_finite())
        }) {
            return Err(OptimizerError::InvalidInput(
                "gradient must have the parameter dimension and finite values",
            ));
        }
        if input.context.max_iterations.is_some_and(|limit| limit == 0)
            || input
                .context
                .max_iterations
                .is_some_and(|limit| input.context.iteration >= limit)
        {
            return Err(OptimizerError::InvalidInput(
                "iteration must be within a positive max_iterations bound",
            ));
        }
        let state = self.state.as_mut().ok_or(OptimizerError::InvalidState)?;
        if input.parameters.len() != state.parameters.len() {
            return Err(OptimizerError::InvalidInput("parameter dimension changed"));
        }
        let improved = state
            .best_objective
            .map(|best| input.objective_value < best)
            .unwrap_or(true);
        if improved {
            state.best_objective = Some(input.objective_value);
            state.parameters = input.parameters;
        } else {
            state.direction = -state.direction;
            state.radius *= 0.5;
        }
        let index = state.coordinate % state.parameters.len();
        state.parameters[index] += state.direction * state.radius;
        state.coordinate = (state.coordinate + 1) % state.parameters.len();
        let bytes = Self::encode(state)?;
        let mut metadata = BTreeMap::new();
        metadata.insert("method".into(), "COBYLA-compatible".into());
        metadata.insert("accepted_observation".into(), improved.to_string());
        metadata.insert("trust_region_radius".into(), state.radius.to_string());
        Ok(StepOutput {
            parameters: state.parameters.clone(),
            state: bytes,
            metadata,
        })
    }
    fn state(&self) -> Result<Vec<u8>, OptimizerError> {
        Self::encode(self.state.as_ref().ok_or(OptimizerError::InvalidState)?)
    }
    fn restore(&mut self, state: &[u8]) -> Result<(), OptimizerError> {
        let parsed: CobylaState =
            serde_json::from_slice(state).map_err(|_| OptimizerError::InvalidState)?;
        if parsed.parameters.is_empty()
            || parsed.parameters.iter().any(|value| !value.is_finite())
            || parsed
                .best_objective
                .is_some_and(|value| !value.is_finite())
            || !parsed.radius.is_finite()
            || parsed.radius <= 0.0
            || parsed.coordinate >= parsed.parameters.len()
            || !matches!(parsed.direction, -1.0 | 1.0)
        {
            return Err(OptimizerError::InvalidState);
        }
        self.state = Some(parsed);
        Ok(())
    }
    fn finalize(&mut self) -> Result<(), OptimizerError> {
        Ok(())
    }
}

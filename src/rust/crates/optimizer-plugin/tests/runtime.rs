use optimizer_plugin::*;
use std::collections::BTreeMap;
fn init() -> InitializeInput {
    InitializeInput {
        parameters: vec![1.0, 2.0],
        metadata: BTreeMap::new(),
    }
}
fn step(parameters: Vec<f64>, objective: f64) -> StepInput {
    StepInput {
        parameters,
        objective_value: objective,
        gradient: None,
        context: IterationContext {
            iteration: 0,
            max_iterations: Some(10),
            metadata: BTreeMap::new(),
        },
    }
}
#[test]
fn cobyla_changes_parameters_after_an_objective_observation() {
    let mut plugin = CobylaPlugin::default();
    plugin.initialize(init()).unwrap();
    let output = plugin.step(step(vec![1.0, 2.0], 4.0)).unwrap();
    assert_ne!(output.parameters, vec![1.0, 2.0]);
    assert_eq!(output.metadata["method"], "COBYLA-compatible");
}
#[test]
fn state_restore_is_exact_and_deterministic() {
    let mut first = CobylaPlugin::default();
    first.initialize(init()).unwrap();
    let _ = first.step(step(vec![1.0, 2.0], 4.0)).unwrap();
    let checkpoint = first.state().unwrap();
    let expected = first.step(step(vec![0.9, 2.0], 3.0)).unwrap();
    let mut restored = CobylaPlugin::default();
    restored.restore(&checkpoint).unwrap();
    assert_eq!(restored.step(step(vec![0.9, 2.0], 3.0)).unwrap(), expected);
}
#[test]
fn lifecycle_rejects_invalid_manifest_and_deactivates() {
    assert!(
        OptimizerPluginRuntime::activate(Box::new(CobylaPlugin::default()), "driver", "1.0.0")
            .is_err()
    );
    let mut runtime =
        OptimizerPluginRuntime::activate(Box::new(CobylaPlugin::default()), "optimizer", "1.0.0")
            .unwrap();
    runtime.plugin_mut().unwrap().initialize(init()).unwrap();
    runtime.deactivate().unwrap();
    assert_eq!(runtime.state(), LifecycleState::Deactivated);
    assert!(runtime.plugin_mut().is_err());
}

struct SecondOptimizer;
impl OptimizerPlugin for SecondOptimizer {
    fn plugin_id(&self) -> &'static str {
        "io.eigen.optimizer.second"
    }
    fn initialize(&mut self, _: InitializeInput) -> Result<Vec<u8>, OptimizerError> {
        Ok(vec![])
    }
    fn step(&mut self, input: StepInput) -> Result<StepOutput, OptimizerError> {
        Ok(StepOutput {
            parameters: input.parameters,
            state: vec![],
            metadata: BTreeMap::new(),
        })
    }
    fn state(&self) -> Result<Vec<u8>, OptimizerError> {
        Ok(vec![])
    }
    fn restore(&mut self, _: &[u8]) -> Result<(), OptimizerError> {
        Ok(())
    }
    fn finalize(&mut self) -> Result<(), OptimizerError> {
        Ok(())
    }
}
#[test]
fn second_compatible_optimizer_uses_the_same_runtime_boundary() {
    assert!(
        OptimizerPluginRuntime::activate(Box::new(SecondOptimizer), "optimizer", "1.0.0").is_ok()
    );
}

#[test]
fn step_rejects_invalid_gradient_and_exhausted_iteration_context() {
    let mut plugin = CobylaPlugin::default();
    plugin.initialize(init()).unwrap();

    let mut invalid_gradient = step(vec![1.0, 2.0], 4.0);
    invalid_gradient.gradient = Some(vec![f64::NAN, 0.0]);
    assert_eq!(
        plugin.step(invalid_gradient),
        Err(OptimizerError::InvalidInput(
            "gradient must have the parameter dimension and finite values"
        ))
    );

    let mut exhausted = step(vec![1.0, 2.0], 4.0);
    exhausted.context.iteration = 10;
    assert_eq!(
        plugin.step(exhausted),
        Err(OptimizerError::InvalidInput(
            "iteration must be within a positive max_iterations bound"
        ))
    );
}

#[test]
fn step_rejects_an_observation_for_a_different_parameter_candidate() {
    let mut plugin = CobylaPlugin::default();
    plugin.initialize(init()).unwrap();
    let expected_state = plugin.state().unwrap();

    assert_eq!(
        plugin.step(step(vec![1.0, 3.0], 4.0)),
        Err(OptimizerError::InvalidInput(
            "parameters do not match the pending optimizer candidate"
        ))
    );
    assert_eq!(plugin.state().unwrap(), expected_state);
}

#[test]
fn restore_rejects_malformed_or_invalid_state() {
    let mut plugin = CobylaPlugin::default();
    assert_eq!(
        plugin.restore(b"not-json"),
        Err(OptimizerError::InvalidState)
    );
    assert_eq!(
        plugin.restore(
            br#"{"parameters":[1.0],"best_objective":null,"radius":0.0,"coordinate":0,"direction":-1.0}"#,
        ),
        Err(OptimizerError::InvalidState)
    );
    assert_eq!(
        plugin.restore(
            br#"{"parameters":[1.0],"best_objective":null,"radius":0.1,"coordinate":1,"direction":-1.0}"#,
        ),
        Err(OptimizerError::InvalidState)
    );
}

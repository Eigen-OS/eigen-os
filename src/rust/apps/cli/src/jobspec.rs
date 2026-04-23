use std::collections::BTreeMap;

pub const JOBSPEC_API_VERSION: &str = "eigen.os/v0.1";
pub const JOBSPEC_KIND: &str = "QuantumJob";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FieldViolation {
    pub field: String,
    pub description: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobSpecValidationError {
    pub code: &'static str,
    pub violations: Vec<FieldViolation>,
}

impl JobSpecValidationError {
    fn new(violations: Vec<FieldViolation>) -> Self {
        Self {
            code: "INVALID_ARGUMENT",
            violations,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobSpec {
    pub api_version: String,
    pub kind: String,
    pub metadata: JobMetadata,
    pub spec: JobRuntimeSpec,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobMetadata {
    pub name: String,
    pub labels: BTreeMap<String, String>,
    pub annotations: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobRuntimeSpec {
    pub program: String,
    pub target: String,
    pub priority: i32,
    pub compiler_options: BTreeMap<String, String>,
    pub metadata: BTreeMap<String, String>,
    pub dependencies: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubmitJobRequest {
    pub name: String,
    pub program: ProgramSource,
    pub target: String,
    pub priority: i32,
    pub compiler_options: BTreeMap<String, String>,
    pub metadata: BTreeMap<String, String>,
    pub dependencies: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProgramSource {
    EigenLangSource { source: String, entrypoint: String },
}

pub fn parse_and_validate_jobspec(yaml: &str) -> Result<JobSpec, JobSpecValidationError> {
    let mut api_version = String::new();
    let mut kind = String::new();
    let mut name = String::new();
    let mut program = String::new();
    let mut target = String::new();
    let mut priority: i32 = 50;
    let mut compiler_options = BTreeMap::new();
    let mut runtime_metadata = BTreeMap::new();
    let mut dependencies = Vec::new();

    let mut section = "";
    let mut subsection = "";
    let mut in_program_block = false;

    for raw_line in yaml.lines() {
        let line = raw_line.trim_end();
        if line.trim().is_empty() || line.trim_start().starts_with('#') {
            continue;
        }

        let indent = raw_line.chars().take_while(|c| *c == ' ').count();

        if in_program_block {
            if indent >= 4 {
                program.push_str(raw_line.trim_start());
                program.push('\n');
                continue;
            }
            in_program_block = false;
        }
        let trimmed = line.trim_start();

        if indent == 0 {
            section = "";
            subsection = "";
            if let Some(v) = value_for(trimmed, "apiVersion:") { api_version = v; continue; }
            if let Some(v) = value_for(trimmed, "kind:") { kind = v; continue; }
            if trimmed == "metadata:" { section = "metadata"; continue; }
            if trimmed == "spec:" { section = "spec"; continue; }
            continue;
        }

        if section == "metadata" && indent == 2 {
            if let Some(v) = value_for(trimmed, "name:") { name = v; continue; }
        }

        if section == "spec" && indent == 2 {
            subsection = "";
            if let Some(v) = value_for(trimmed, "program:") {
                if v == "|" {
                    in_program_block = true;
                } else {
                    program = v;
                }
                continue;
            }
            if let Some(v) = value_for(trimmed, "target:") { target = v; continue; }
            if let Some(v) = value_for(trimmed, "priority:") {
                if let Ok(parsed) = v.parse::<i32>() { priority = parsed; }
                continue;
            }
            if trimmed == "compiler_options:" { subsection = "compiler_options"; continue; }
            if trimmed == "metadata:" { subsection = "runtime_metadata"; continue; }
            if trimmed == "dependencies:" { subsection = "dependencies"; continue; }
        }

        if section == "spec" && indent >= 4 {
            match subsection {
                "compiler_options" => {
                    if let Some((k, v)) = kv_pair(trimmed) { compiler_options.insert(k, v); }
                }
                "runtime_metadata" => {
                    if let Some((k, v)) = kv_pair(trimmed) { runtime_metadata.insert(k, v); }
                }
                "dependencies" => {
                    if let Some(dep) = trimmed.strip_prefix('-') { dependencies.push(strip_quotes(dep.trim())); }
                }
                _ => {}
            }
        }
    }

    program = program.trim_end().to_string();

    let mut violations = Vec::new();
    if api_version.is_empty() {
        violations.push(FieldViolation { field: "apiVersion".to_string(), description: "field is required".to_string() });
    } else if api_version != JOBSPEC_API_VERSION {
        violations.push(FieldViolation { field: "apiVersion".to_string(), description: format!("must be '{JOBSPEC_API_VERSION}'") });
    }
    if kind.is_empty() {
        violations.push(FieldViolation { field: "kind".to_string(), description: "field is required".to_string() });
    } else if kind != JOBSPEC_KIND {
        violations.push(FieldViolation { field: "kind".to_string(), description: format!("must be '{JOBSPEC_KIND}'") });
    }
    if name.is_empty() {
        violations.push(FieldViolation { field: "metadata.name".to_string(), description: "field is required".to_string() });
    }
    if program.is_empty() {
        violations.push(FieldViolation { field: "spec.program".to_string(), description: "field is required".to_string() });
    }
    if target.is_empty() {
        violations.push(FieldViolation { field: "spec.target".to_string(), description: "field is required".to_string() });
    }
    if !(0..=100).contains(&priority) {
        violations.push(FieldViolation { field: "spec.priority".to_string(), description: "must be between 0 and 100".to_string() });
    }

    if !violations.is_empty() {
        return Err(JobSpecValidationError::new(violations));
    }

    Ok(JobSpec {
        api_version,
        kind,
        metadata: JobMetadata { name, labels: BTreeMap::new(), annotations: BTreeMap::new() },
        spec: JobRuntimeSpec {
            program,
            target,
            priority,
            compiler_options,
            metadata: runtime_metadata,
            dependencies,
        },
    })
}

fn value_for(line: &str, prefix: &str) -> Option<String> {
    line.strip_prefix(prefix).map(|v| strip_quotes(v.trim()))
}

fn kv_pair(line: &str) -> Option<(String, String)> {
    let (k, v) = line.split_once(':')?;
    Some((k.trim().to_string(), strip_quotes(v.trim())))
}

fn strip_quotes(s: &str) -> String {
    s.trim_matches('"').trim_matches('\'').to_string()
}

pub fn map_to_submit_job_request(job: &JobSpec) -> SubmitJobRequest {
    SubmitJobRequest {
        name: job.metadata.name.clone(),
        program: ProgramSource::EigenLangSource { source: job.spec.program.clone(), entrypoint: "main".to_string() },
        target: job.spec.target.clone(),
        priority: job.spec.priority,
        compiler_options: job.spec.compiler_options.clone(),
        metadata: job.spec.metadata.clone(),
        dependencies: job.spec.dependencies.clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_fixture_minimal_round_trip_maps_to_submit_job() {
        let yaml = include_str!("../tests/fixtures/jobspec-valid-minimal.yaml");
        let spec = parse_and_validate_jobspec(yaml).expect("valid spec");
        let req = map_to_submit_job_request(&spec);
        assert_eq!(req.name, "bell-state");
        assert_eq!(req.target, "sim:local");
        assert_eq!(req.priority, 50);
    }

    #[test]
    fn valid_fixture_full_round_trip_maps_to_submit_job() {
        let yaml = include_str!("../tests/fixtures/jobspec-valid-full.yaml");
        let spec = parse_and_validate_jobspec(yaml).expect("valid spec");
        let req = map_to_submit_job_request(&spec);
        assert_eq!(req.name, "vqe-h2");
        assert_eq!(req.priority, 10);
        assert_eq!(req.compiler_options.get("optimization_level"), Some(&"1".to_string()));
        assert_eq!(req.metadata.get("shots"), Some(&"1024".to_string()));
        assert_eq!(req.dependencies.len(), 2);
    }

    #[test]
    fn valid_fixture_ignores_unknown_top_level_and_maps() {
        let yaml = include_str!("../tests/fixtures/jobspec-valid-unknown-keys.yaml");
        let spec = parse_and_validate_jobspec(yaml).expect("valid spec");
        let req = map_to_submit_job_request(&spec);
        assert_eq!(req.name, "qaoa-maxcut");
        assert_eq!(req.target, "ibmq:quito");
        assert_eq!(req.priority, 50);
    }

    #[test]
    fn invalid_spec_reports_invalid_argument_with_field_violations() {
        let yaml = r#"
apiVersion: nope/v9
kind: WrongKind
metadata: {}
spec:
  target: sim:local
  priority: 900
"#;
        let err = parse_and_validate_jobspec(yaml).expect_err("must fail");
        assert_eq!(err.code, "INVALID_ARGUMENT");
        assert!(err.violations.iter().any(|v| v.field == "apiVersion"));
        assert!(err.violations.iter().any(|v| v.field == "kind"));
        assert!(err.violations.iter().any(|v| v.field == "metadata.name"));
        assert!(err.violations.iter().any(|v| v.field == "spec.program"));
        assert!(err.violations.iter().any(|v| v.field == "spec.priority"));
    }
}

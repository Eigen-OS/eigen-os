use std::collections::{BTreeMap, HashMap};
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use tokio::runtime::{Handle, Runtime};
use tokio::task;
use tonic::transport::{Channel, Endpoint, Error as TransportError};

#[cfg(test)]
use tonic::{Request, Response, Status};

pub mod eigen {
    pub mod api {
        pub mod v1 {
            tonic::include_proto!("eigen.api.v1");
        }
    }
}

pub const JOBSPEC_API_VERSION: &str = "eigen.os/v1";
pub const LEGACY_JOBSPEC_API_VERSION: &str = "eigen.os/v0.1";
pub const JOBSPEC_CONTRACT_VERSION: &str = "1.0.0";
pub const JOBSPEC_KIND: &str = "QuantumJob";
pub const JOBSPEC_WORKLOAD_KINDS: [&str; 6] = [
    "QuantumJob",
    "HybridWorkflow",
    "DistributedJob",
    "BenchmarkJob",
    "PipelineJob",
    "ReplayJob",
];
pub const JOBSPEC_WORKLOAD_KIND_DEFAULT: &str = "QuantumJob";
pub const EIGEN_LANG_RUNTIME_HINTS_VERSION: &str = "1.1.0";
pub const EIGEN_LANG_RUNTIME_DIAGNOSTICS_VERSION: &str = "1.0.0";
pub const EIGEN_LANG_EXECUTION_ANNOTATIONS_VERSION: &str = "1.0.0";
pub const PUBLIC_ENVELOPE_CONTRACT_VERSION: &str = "1.0.0";
pub const DEFAULT_TENANT_ID: &str = "tenant-default";
pub const DEFAULT_PROJECT_ID: &str = "project-default";
pub const CLI_CLIENT_VERSION: &str = "eigen-cli/0.16.0";


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

impl Display for JobSpecValidationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: ", self.code)?;
        for (idx, v) in self.violations.iter().enumerate() {
            if idx > 0 {
                write!(f, "; ")?;
            }
            write!(f, "{} {}", v.field, v.description)?;
        }
        Ok(())
    }
}

impl std::error::Error for JobSpecValidationError {}

impl JobSpecValidationError {
    fn new(violations: Vec<FieldViolation>) -> Self {
        Self {
            code: "INVALID_ARGUMENT",
            violations,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SubmitBuildError {
    Io(String),
    Validation(JobSpecValidationError),
}

impl Display for SubmitBuildError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            SubmitBuildError::Io(e) => write!(f, "{e}"),
            SubmitBuildError::Validation(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for SubmitBuildError {}

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
    pub program_inline: Option<String>,
    pub program_path: Option<String>,
    pub entrypoint: String,
    pub target: String,
    pub priority: i32,
    pub compiler_options: BTreeMap<String, String>,
    pub metadata: BTreeMap<String, String>,
    pub dependencies: Vec<String>,
    pub workload: WorkloadContract,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkloadContract {
    pub kind: String,
    pub execution_profile: String,
    pub replayable: bool,
    pub artifact_lineage: WorkloadArtifactLineage,
    pub observability: WorkloadObservability,
    pub security: WorkloadSecurity,
    pub backend_target: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct WorkloadArtifactLineage {
    pub execution_ref: String,
    pub parent_ref: String,
    pub policy_snapshot_ref: String,
    pub root_ref: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct WorkloadObservability {
    pub emit_metrics: bool,
    pub trace_id: String,
    pub trace_ref: String,
    pub traceparent: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct WorkloadSecurity {
    pub fail_closed: bool,
    pub policy_snapshot_ref: String,
    pub project_id: String,
    pub service_identity: String,
    pub tenant_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubmitJobRequest {
    pub jobspec_api_version: String,
    pub name: String,
    pub program: ProgramSource,
    pub target: String,
    pub priority: i32,
    pub compiler_options: BTreeMap<String, String>,
    pub metadata: BTreeMap<String, String>,
    pub dependencies: Vec<String>,
    pub workload: WorkloadContract,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProgramSource {
    EigenLangSource {
        source: String,
        entrypoint: String,
        sha256: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubmitJobResponse {
    pub job_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicSubmitEnvelope {
    pub contract_version: String,
    pub request_id: String,
    pub idempotency_key: String,
    pub traceparent: String,
    pub tenant_id: String,
    pub project_id: String,
    pub client_version: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct PublicSubmitOptions {
    pub request_id: Option<String>,
    pub idempotency_key: Option<String>,
    pub traceparent: Option<String>,
    pub tenant_id: Option<String>,
    pub project_id: Option<String>,
    pub client_version: Option<String>,
}

pub fn build_submit_request_from_job_file(
    path: &Path,
) -> Result<SubmitJobRequest, SubmitBuildError> {
    let yaml = fs::read_to_string(path)
        .map_err(|e| SubmitBuildError::Io(format!("failed to read {}: {e}", path.display())))?;
    let spec = parse_and_validate_jobspec(&yaml).map_err(SubmitBuildError::Validation)?;

    let basedir = path.parent().unwrap_or_else(|| Path::new("."));
    map_to_submit_job_request_with_packaging(&spec, basedir).map_err(SubmitBuildError::Validation)
}

pub fn parse_and_validate_jobspec(yaml: &str) -> Result<JobSpec, JobSpecValidationError> {
    let mut api_version = String::new();
    let mut kind = String::new();
    let mut name = String::new();

    let mut program_inline = None;
    let mut program_path = None;
    let mut entrypoint = "main".to_string();
    let mut target = String::new();
    let mut priority: i32 = 50;
    let mut compiler_options = BTreeMap::new();
    let mut runtime_metadata = BTreeMap::new();
    let mut dependencies = Vec::new();

    let mut workload_kind = JOBSPEC_WORKLOAD_KIND_DEFAULT.to_string();
    let mut workload_execution_profile = String::new();
    let mut workload_replayable: Option<bool> = None;
    let mut workload_backend_target = String::new();
    let mut workload_artifact_root_ref = String::new();
    let mut workload_artifact_parent_ref = String::new();
    let mut workload_artifact_policy_snapshot_ref = String::new();
    let mut workload_artifact_execution_ref = String::new();
    let mut workload_observability_emit_metrics: Option<bool> = None;
    let mut workload_observability_trace_id = String::new();
    let mut workload_observability_trace_ref = String::new();
    let mut workload_observability_traceparent = String::new();
    let mut workload_security_fail_closed: Option<bool> = None;
    let mut workload_security_policy_snapshot_ref = String::new();
    let mut workload_security_project_id = String::new();
    let mut workload_security_service_identity = String::new();
    let mut workload_security_tenant_id = String::new();

    let mut section = "";
    let mut subsection = "";
    let mut in_program_block = false;
    let mut program_buf = String::new();

    for raw_line in yaml.lines() {
        let line = raw_line.trim_end();
        if line.trim().is_empty() || line.trim_start().starts_with('#') {
            continue;
        }

        let indent = raw_line.chars().take_while(|c| *c == ' ').count();

        if in_program_block {
            if indent >= 4 {
                program_buf.push_str(raw_line.trim_start());
                program_buf.push('\n');
                continue;
            }
            in_program_block = false;
            program_inline = Some(program_buf.trim_end().to_string());
        }
        let trimmed = line.trim_start();

        if indent == 0 {
            section = "";
            subsection = "";
            if let Some(v) = value_for(trimmed, "apiVersion:") {
                api_version = v;
                continue;
            }
            if let Some(v) = value_for(trimmed, "kind:") {
                kind = v;
                continue;
            }
            if trimmed == "metadata:" {
                section = "metadata";
                continue;
            }
            if trimmed == "spec:" {
                section = "spec";
                continue;
            }
            continue;
        }

        if section == "metadata" && indent == 2 {
            if let Some(v) = value_for(trimmed, "name:") {
                name = v;
                continue;
            }
        }

        if section == "spec" && indent == 2 {
            subsection = "";
            if let Some(v) = value_for(trimmed, "program:") {
                if v == "|" {
                    in_program_block = true;
                    program_buf.clear();
                } else if v.is_empty() {
                    subsection = "program";
                } else {
                    program_inline = Some(v);
                }
                continue;
            }
            if let Some(v) = value_for(trimmed, "program_path:") {
                program_path = Some(v);
                continue;
            }
            if let Some(v) = value_for(trimmed, "entrypoint:") {
                entrypoint = v;
                continue;
            }
            if let Some(v) = value_for(trimmed, "target:") {
                target = v;
                continue;
            }
            if let Some(v) = value_for(trimmed, "priority:") {
                if let Ok(parsed) = v.parse::<i32>() {
                    priority = parsed;
                }
                continue;
            }
            if trimmed == "compiler_options:" || trimmed == "compiler:" {
                subsection = "compiler_options";
                continue;
            }
            if trimmed == "metadata:" {
                subsection = "runtime_metadata";
                continue;
            }
            if trimmed == "dependencies:" {
                subsection = "dependencies";
                continue;
            }
            if trimmed == "workload:" {
                subsection = "workload";
                continue;
            }
        }

        if section == "spec" && indent >= 4 {
            match subsection {
                "compiler_options" => {
                    if let Some((k, v)) = kv_pair(trimmed) {
                        compiler_options.insert(k, v);
                    }
                }
                "runtime_metadata" => {
                    if let Some((k, v)) = kv_pair(trimmed) {
                        runtime_metadata.insert(k, v);
                    }
                }
                "dependencies" => {
                    if let Some(dep) = trimmed.strip_prefix('-') {
                        dependencies.push(strip_quotes(dep.trim()));
                    }
                }
                "program" => {
                    if let Some(v) = value_for(trimmed, "path:") {
                        program_path = Some(v);
                    } else if let Some(v) = value_for(trimmed, "source:") {
                        if v == "|" {
                            in_program_block = true;
                            program_buf.clear();
                        } else {
                            program_inline = Some(v);
                        }
                    }
                }
                "workload" => {
                    if let Some(v) = value_for(trimmed, "kind:") {
                        workload_kind = v;
                        continue;
                    }
                    if let Some(v) = value_for(trimmed, "execution_profile:") {
                        workload_execution_profile = v;
                        continue;
                    }
                    if let Some(v) = value_for(trimmed, "replayable:") {
                        if let Ok(parsed) = v.parse::<bool>() {
                            workload_replayable = Some(parsed);
                        }
                        continue;
                    }
                    if let Some(v) = value_for(trimmed, "backend_target:") {
                        workload_backend_target = v;
                        continue;
                    }
                    if trimmed == "artifact_lineage:" {
                        subsection = "workload_artifact_lineage";
                        continue;
                    }
                    if trimmed == "observability:" {
                        subsection = "workload_observability";
                        continue;
                    }
                    if trimmed == "security:" {
                        subsection = "workload_security";
                        continue;
                    }
                }
                "workload_artifact_lineage" => {
                    if let Some(v) = value_for(trimmed, "root_ref:") {
                        workload_artifact_root_ref = v;
                    } else if let Some(v) = value_for(trimmed, "parent_ref:") {
                        workload_artifact_parent_ref = v;
                    } else if let Some(v) = value_for(trimmed, "policy_snapshot_ref:") {
                        workload_artifact_policy_snapshot_ref = v;
                    } else if let Some(v) = value_for(trimmed, "execution_ref:") {
                        workload_artifact_execution_ref = v;
                    }
                }
                "workload_observability" => {
                    if let Some(v) = value_for(trimmed, "traceparent:") {
                        workload_observability_traceparent = v;
                    } else if let Some(v) = value_for(trimmed, "trace_id:") {
                        workload_observability_trace_id = v;
                    } else if let Some(v) = value_for(trimmed, "trace_ref:") {
                        workload_observability_trace_ref = v;
                    } else if let Some(v) = value_for(trimmed, "emit_metrics:") {
                        if let Ok(parsed) = v.parse::<bool>() {
                            workload_observability_emit_metrics = Some(parsed);
                        }
                    }
                }
                "workload_security" => {
                    if let Some(v) = value_for(trimmed, "tenant_id:") {
                        workload_security_tenant_id = v;
                    } else if let Some(v) = value_for(trimmed, "project_id:") {
                        workload_security_project_id = v;
                    } else if let Some(v) = value_for(trimmed, "service_identity:") {
                        workload_security_service_identity = v;
                    } else if let Some(v) = value_for(trimmed, "policy_snapshot_ref:") {
                        workload_security_policy_snapshot_ref = v;
                    } else if let Some(v) = value_for(trimmed, "fail_closed:") {
                        if let Ok(parsed) = v.parse::<bool>() {
                            workload_security_fail_closed = Some(parsed);
                        }
                    }
                }
                _ => {}
            }
        }
    }

    if in_program_block {
        program_inline = Some(program_buf.trim_end().to_string());
    }

    let mut violations = Vec::new();
    if api_version.is_empty() {
        violations.push(FieldViolation {
            field: "apiVersion".to_string(),
            description: "field is required".to_string(),
        });
    } else if api_version != JOBSPEC_API_VERSION && api_version != LEGACY_JOBSPEC_API_VERSION {
        violations.push(FieldViolation {
            field: "apiVersion".to_string(),
            description: format!("must be '{JOBSPEC_API_VERSION}'"),
        });
    }
    if kind.is_empty() {
        violations.push(FieldViolation {
            field: "kind".to_string(),
            description: "field is required".to_string(),
        });
    } else if kind != JOBSPEC_KIND {
        violations.push(FieldViolation {
            field: "kind".to_string(),
            description: format!("must be '{JOBSPEC_KIND}'"),
        });
    }
    if name.is_empty() {
        violations.push(FieldViolation {
            field: "kind".to_string(),
            description: "field is required".to_string(),
        });
    }
    // Removed early check for spec.program – defaulting to program.eigen.py is handled later.
    if target.is_empty() {
        violations.push(FieldViolation {
            field: "spec.target".to_string(),
            description: "field is required".to_string(),
        });
    }
    if entrypoint.trim().is_empty() {
        violations.push(FieldViolation {
            field: "spec.entrypoint".to_string(),
            description: "must not be empty".to_string(),
        });
    }
    if !(0..=100).contains(&priority) {
        violations.push(FieldViolation {
            field: "spec.priority".to_string(),
            description: "must be between 0 and 100".to_string(),
        });
    }

    if !JOBSPEC_WORKLOAD_KINDS.contains(&workload_kind.as_str()) {
        violations.push(FieldViolation {
            field: "spec.workload.kind".to_string(),
            description: format!("must be one of {}", JOBSPEC_WORKLOAD_KINDS.join(", ")),
        });
        workload_kind = JOBSPEC_WORKLOAD_KIND_DEFAULT.to_string();
    }
    if workload_execution_profile.trim().is_empty() {
        workload_execution_profile = match workload_kind.as_str() {
            "QuantumJob" => "quantum",
            "HybridWorkflow" => "hybrid",
            "DistributedJob" => "distributed",
            "BenchmarkJob" => "benchmark",
            "PipelineJob" => "pipeline",
            "ReplayJob" => "replay",
            _ => "quantum",
        }
        .to_string();
    }
    let workload_replayable = workload_replayable.unwrap_or_else(|| workload_kind != "QuantumJob");
    let workload_observability_emit_metrics = workload_observability_emit_metrics.unwrap_or(false);
    let workload_security_fail_closed = workload_security_fail_closed.unwrap_or(workload_kind == "ReplayJob");

    if !violations.is_empty() {
        return Err(JobSpecValidationError::new(violations));
    }

    Ok(JobSpec {
        api_version,
        kind,
        metadata: JobMetadata {
            name,
            labels: BTreeMap::new(),
            annotations: BTreeMap::new(),
        },
        spec: JobRuntimeSpec {
            program_inline,
            program_path,
            entrypoint,
            target: target.clone(),
            priority,
            compiler_options,
            metadata: runtime_metadata,
            dependencies,
            workload: WorkloadContract {
                kind: workload_kind,
                execution_profile: workload_execution_profile,
                replayable: workload_replayable,
                artifact_lineage: WorkloadArtifactLineage {
                    execution_ref: workload_artifact_execution_ref,
                    parent_ref: workload_artifact_parent_ref,
                    policy_snapshot_ref: workload_artifact_policy_snapshot_ref,
                    root_ref: workload_artifact_root_ref,
                },
                observability: WorkloadObservability {
                    emit_metrics: workload_observability_emit_metrics,
                    trace_id: workload_observability_trace_id,
                    trace_ref: workload_observability_trace_ref,
                    traceparent: workload_observability_traceparent,
                },
                security: WorkloadSecurity {
                    fail_closed: workload_security_fail_closed,
                    policy_snapshot_ref: workload_security_policy_snapshot_ref,
                    project_id: workload_security_project_id,
                    service_identity: workload_security_service_identity,
                    tenant_id: workload_security_tenant_id,
                },
                backend_target: workload_backend_target,
            },
        },
    })
}

pub fn map_to_submit_job_request_with_packaging(
    job: &JobSpec,
    basedir: &Path,
) -> Result<SubmitJobRequest, JobSpecValidationError> {
    let mut violations = Vec::new();

    let inline_source = job
        .spec
        .program_inline
        .as_ref()
        .filter(|s| !s.trim().is_empty());
    if inline_source.is_some() && job.spec.program_path.is_some() 
    {
        violations.push(FieldViolation {
            field: "spec.program".to_string(),
            description: "must choose exactly one source mode: inline source or path".to_string(),
        });
    }

    let source = if let Some(source) = inline_source {
        source.to_string()
    } else {
        let path = job
            .spec
            .program_path
            .clone()
            .unwrap_or_else(|| "program.eigen.py".to_string());
        validate_safe_relative_path(&path)?;
        let program_path = resolve_program_path(basedir, &path);

        if !program_path.exists() {
            violations.push(FieldViolation {
                field: "spec.program_path".to_string(),
                description: format!("file not found: {}", program_path.display()),
            });
        }

   if !violations.is_empty() {
            return Err(JobSpecValidationError::new(violations));
        }

        fs::read_to_string(&program_path).map_err(|e| {
            JobSpecValidationError::new(vec![FieldViolation {
                field: "spec.program_path".to_string(),
                description: format!("failed reading {}: {e}", program_path.display()),
            }])
        })?
    };

    if !violations.is_empty() {
        return Err(JobSpecValidationError::new(violations));
    }

    validate_entrypoint(&source, &job.spec.entrypoint)?;

    let sha256 = sha256_hex(source.as_bytes());

    let mut metadata = job.spec.metadata.clone();
    metadata.insert("source_sha256".to_string(), sha256.clone());
    metadata.insert(
        "jobspec_workload".to_string(),
        workload_json(&job.spec.workload),
    );

    Ok(SubmitJobRequest {
        jobspec_api_version: job.api_version.clone(),
        name: job.metadata.name.clone(),
        program: ProgramSource::EigenLangSource {
            source,
            entrypoint: job.spec.entrypoint.clone(),
            sha256,
        },
        target: job.spec.target.clone(),
        priority: job.spec.priority,
        compiler_options: job.spec.compiler_options.clone(),
        metadata,
        dependencies: job.spec.dependencies.clone(),
        workload: job.spec.workload.clone(),
    })
}

pub fn canonical_jobspec_json_from_request(
    req: &SubmitJobRequest,
    input_api_version: &str,
) -> String {
    let ProgramSource::EigenLangSource {
        source,
        entrypoint,
        sha256,
    } = &req.program;
    let migration = if input_api_version == LEGACY_JOBSPEC_API_VERSION {
        "v0.1-inline-and-program_path"
    } else {
        "none"
    };
    let mut metadata = req.metadata.clone();
    metadata.remove("jobspec_yaml");
    let base = format!(
        concat!(
            "{{",
            "\"apiVersion\":\"{api_version}\",",
            "\"compatibility\":{{\"input_apiVersion\":\"{input_api_version}\",\"migration\":\"{migration}\"}},",
            "\"contract\":\"jobspec.normalized\",",
            "\"kind\":\"QuantumJob\",",
            "\"metadata\":{{\"annotations\":{{}},\"labels\":{{}},\"name\":\"{name}\"}},",
            "\"observability\":{{}},",
            "\"scheduling\":{{}},",
            "\"security\":{{}},",
            "\"spec\":{{",
            "\"compiler_options\":{compiler_options},",
            "\"dependencies\":{dependencies},",
            "\"metadata\":{metadata},",
            "\"priority\":{priority},",
            "\"program\":{{\"entrypoint\":\"{entrypoint}\",\"sha256\":\"{sha256}\",\"source\":\"{source}\"}},",
            "\"target\":\"{target}\",",
            "\"workload\":{workload}",
            "}},",
            "\"version\":\"{version}\"",
            "}}"
        ),
        api_version = JOBSPEC_API_VERSION,
        input_api_version = json_escape(input_api_version),
        migration = migration,
        name = json_escape(&req.name),
        compiler_options = string_map_json(&req.compiler_options),
        dependencies = string_vec_json(&req.dependencies),
        metadata = string_map_json(&metadata),
        priority = req.priority,
        entrypoint = json_escape(entrypoint),
        sha256 = json_escape(sha256),
        source = json_escape(source),
        target = json_escape(&req.target),
        workload = workload_json(&req.workload),
        version = JOBSPEC_CONTRACT_VERSION,
    );
    let digest = sha256_hex(base.as_bytes());
    format!("{{\"digest\":\"{}\",\"normalized\":{}}}", digest, base)
}

pub fn canonical_jobspec_digest_from_request(
    req: &SubmitJobRequest,
    input_api_version: &str,
) -> String {
    let canonical = canonical_jobspec_json_from_request(req, input_api_version);
    sha256_hex(canonical.as_bytes())
}

fn string_map_json(map: &BTreeMap<String, String>) -> String {
    let mut parts = Vec::new();
    for (k, v) in map {
        parts.push(format!("\"{}\":\"{}\"", json_escape(k), json_escape(v)));
    }
    format!("{{{}}}", parts.join(","))
}

fn string_vec_json(values: &[String]) -> String {
    let parts: Vec<String> = values
        .iter()
        .map(|v| format!("\"{}\"", json_escape(v)))
        .collect();
    format!("[{}]", parts.join(","))
}

fn workload_json(workload: &WorkloadContract) -> String {
    let artifact = &workload.artifact_lineage;
    let observability = &workload.observability;
    let security = &workload.security;
    format!(
        r#"{{"artifact_lineage":{{"execution_ref":"{}","parent_ref":"{}","policy_snapshot_ref":"{}","root_ref":"{}"}},"backend_target":"{}","execution_profile":"{}","kind":"{}","observability":{{"emit_metrics":{},"trace_id":"{}","trace_ref":"{}","traceparent":"{}"}},"replayable":{},"security":{{"fail_closed":{},"policy_snapshot_ref":"{}","project_id":"{}","service_identity":"{}","tenant_id":"{}"}}}}"#,
        json_escape(&artifact.execution_ref),
        json_escape(&artifact.parent_ref),
        json_escape(&artifact.policy_snapshot_ref),
        json_escape(&artifact.root_ref),
        json_escape(&workload.backend_target),
        json_escape(&workload.execution_profile),
        json_escape(&workload.kind),
        workload.observability.emit_metrics,
        json_escape(&observability.trace_id),
        json_escape(&observability.trace_ref),
        json_escape(&observability.traceparent),
        workload.replayable,
        security.fail_closed,
        json_escape(&security.policy_snapshot_ref),
        json_escape(&security.project_id),
        json_escape(&security.service_identity),
        json_escape(&security.tenant_id),
    )
}

fn default_workload_contract() -> WorkloadContract {
    WorkloadContract {
        kind: JOBSPEC_WORKLOAD_KIND_DEFAULT.to_string(),
        execution_profile: "quantum".to_string(),
        replayable: false,
        artifact_lineage: WorkloadArtifactLineage::default(),
        observability: WorkloadObservability::default(),
        security: WorkloadSecurity::default(),
        backend_target: String::new(),
    }
}

fn runtime() -> Result<&'static Runtime, GrpcLikeError> {
    static RT: OnceLock<Result<Runtime, String>> = OnceLock::new();
    match RT.get_or_init(|| Runtime::new().map_err(|e| e.to_string())) {
        Ok(rt) => Ok(rt),
        Err(msg) => Err(GrpcLikeError {
            code: GrpcCode::Internal,
            message: format!("failed to create tokio runtime: {msg}"),
            retry_hint: None,
        }),
    }
}

fn block_on_result<F, T>(future: F) -> Result<T, GrpcLikeError>
where
    F: std::future::Future<Output = Result<T, GrpcLikeError>>,
{
    if Handle::try_current().is_ok() {
        task::block_in_place(|| Handle::current().block_on(future))
    } else {
        runtime()?.block_on(future)
    }
}

#[cfg(not(test))]
fn system_api_endpoint() -> String {
    std::env::var("EIGEN_SYSTEM_API_ENDPOINT").unwrap_or_else(|_| "http://127.0.0.1:50051".to_string())
}

#[cfg(test)]
fn system_api_endpoint() -> String {
    std::env::var("EIGEN_SYSTEM_API_ENDPOINT").unwrap_or_else(|_| test_system_api_endpoint())
}

#[cfg(test)]
fn test_system_api_endpoint() -> String {
    use std::fs;
    use std::net::SocketAddr;
    use std::sync::{mpsc, OnceLock as StdOnceLock};

    use tokio::net::TcpListener;
    use tokio::runtime::Builder;
    use tokio_stream::wrappers::TcpListenerStream;

    static ENDPOINT: StdOnceLock<String> = StdOnceLock::new();
    ENDPOINT
        .get_or_init(|| {
            let qfs_root = std::env::temp_dir()
                .join("eigen-cli-qfs-fixture")
                .join(std::process::id().to_string());
            let qfs_results = qfs_root.join("jobs/job-demo-done/results.parquet");
            fs::create_dir_all(qfs_results.parent().expect("qfs parent"))
                .expect("create qfs fixture directory");
            fs::write(&qfs_results, b"PAR1fixturePAR1").expect("write qfs fixture");
            unsafe {
                std::env::set_var("EIGEN_QFS_LOCAL_ROOT", &qfs_root);
            }

            let (addr_tx, addr_rx) = mpsc::channel::<SocketAddr>();
            std::thread::spawn(move || {
                let rt = Builder::new_multi_thread()
                    .enable_all()
                    .build()
                    .expect("fixture runtime");
                rt.block_on(async move {
                    let listener = TcpListener::bind("127.0.0.1:0")
                        .await
                        .expect("bind fixture port");
                    let addr = listener.local_addr().expect("fixture addr");
                    addr_tx.send(addr).expect("send fixture addr");

                    let incoming = TcpListenerStream::new(listener);
                    let service =
                        eigen::api::v1::job_service_server::JobServiceServer::new(TestJobService);
                    tonic::transport::Server::builder()
                        .add_service(service)
                        .serve_with_incoming(incoming)
                        .await
                        .expect("serve fixture api");
                });
            });

            let addr = addr_rx.recv().expect("receive fixture addr");
            format!("http://{addr}")
        })
        .clone()
}

#[cfg(test)]
struct TestJobService;

#[cfg(test)]
#[tonic::async_trait]
impl eigen::api::v1::job_service_server::JobService for TestJobService {
    type StreamJobUpdatesStream = std::pin::Pin<
        Box<
            dyn tokio_stream::Stream<
                    Item = Result<eigen::api::v1::StreamJobUpdatesResponse, Status>,
                > + Send
                + 'static,
        >,
    >;

    async fn submit_job(
        &self,
        _request: Request<eigen::api::v1::SubmitJobRequest>,
    ) -> Result<Response<eigen::api::v1::SubmitJobResponse>, Status> {
        Ok(Response::new(eigen::api::v1::SubmitJobResponse {
            job_id: "job-fixture-submit".to_string(),
            ..Default::default()
        }))
    }

    async fn get_job_status(
        &self,
        request: Request<eigen::api::v1::GetJobStatusRequest>,
    ) -> Result<Response<eigen::api::v1::GetJobStatusResponse>, Status> {
        let job_id = request.into_inner().job_id;
        let (state, stage, progress, message) = match job_id.as_str() {
            "job-demo" => (4, "RUNNING", 42.0_f32, "running"),
            "job-demo-done" => (5, "DONE", 100.0_f32, "done"),
            "job-demo-error" => (6, "ERROR", 100.0_f32, "failed"),
            _ => return Err(Status::not_found("unknown job_id in fixture server")),
        };

        Ok(Response::new(eigen::api::v1::GetJobStatusResponse {
            status: Some(eigen::api::v1::JobStatus {
                job_id,
                state,
                stage: stage.to_string(),
                progress,
                message: message.to_string(),
                ..Default::default()
            }),
        }))
    }

    async fn cancel_job(
        &self,
        _request: Request<eigen::api::v1::CancelJobRequest>,
    ) -> Result<Response<eigen::api::v1::CancelJobResponse>, Status> {
        Ok(Response::new(eigen::api::v1::CancelJobResponse {
            accepted: true,
            ..Default::default()
        }))
    }

    async fn stream_job_updates(
        &self,
        request: Request<eigen::api::v1::StreamJobUpdatesRequest>,
    ) -> Result<Response<Self::StreamJobUpdatesStream>, Status> {
        let job_id = request.into_inner().job_id;
        if job_id != "job-demo" {
            return Err(Status::not_found("unknown job_id in fixture server"));
        }

        let updates = vec![
            Ok(eigen::api::v1::StreamJobUpdatesResponse {
                update: Some(eigen::api::v1::JobUpdate {
                    event_seq: 1,
                    state: 1,
                    stage: "PENDING".to_string(),
                    progress: 0.0,
                    message: "queued".to_string(),
                    ..Default::default()
                }),
            }),
            Ok(eigen::api::v1::StreamJobUpdatesResponse {
                update: Some(eigen::api::v1::JobUpdate {
                    event_seq: 2,
                    state: 4,
                    stage: "RUNNING".to_string(),
                    progress: 42.0,
                    message: "running".to_string(),
                    ..Default::default()
                }),
            }),
            Ok(eigen::api::v1::StreamJobUpdatesResponse {
                update: Some(eigen::api::v1::JobUpdate {
                    event_seq: 3,
                    state: 5,
                    stage: "DONE".to_string(),
                    progress: 100.0,
                    message: "done".to_string(),
                    ..Default::default()
                }),
            }),
        ];
        Ok(Response::new(Box::pin(tokio_stream::iter(updates))))
    }

    async fn get_job_results(
        &self,
        request: Request<eigen::api::v1::GetJobResultsRequest>,
    ) -> Result<Response<eigen::api::v1::GetJobResultsResponse>, Status> {
        let job_id = request.into_inner().job_id;
        match job_id.as_str() {
            "job-demo-done" => Ok(Response::new(eigen::api::v1::GetJobResultsResponse {
                job_id,
                state: 5,
                counts: std::collections::HashMap::from([
                    ("00".to_string(), 512),
                    ("11".to_string(), 512),
                ]),
                metadata: std::collections::HashMap::from([
                    (
                        "qfs_result_ref".to_string(),
                        format!("qfs://jobs/{}/results.parquet", "job-demo-done"),
                    ),
                ]),
                ..Default::default()
            })),
            "job-demo-error" => Ok(Response::new(eigen::api::v1::GetJobResultsResponse {
                job_id,
                state: 6,
                error_code: "EIGEN_SIM_ERROR".to_string(),
                error_summary: "failed to simulate fixture job".to_string(),
                metadata: std::collections::HashMap::from([
                    (
                        "qfs_result_ref".to_string(),
                        format!("qfs://jobs/{}/results.parquet", "job-demo-error"),
                    ),
                ]),
                ..Default::default()
            })),
            _ => Err(Status::not_found("unknown job_id in fixture server")),
        }
    }

    async fn get_dispatch_rationale(
        &self,
        request: Request<eigen::api::v1::GetDispatchRationaleRequest>,
    ) -> Result<Response<eigen::api::v1::GetDispatchRationaleResponse>, Status> {
        let job_id = request.into_inner().job_id;
        if job_id != "job-demo" {
            return Err(Status::not_found("unknown job_id in fixture server"));
        }

        Ok(Response::new(eigen::api::v1::GetDispatchRationaleResponse {
            rationale: Some(eigen::api::v1::DispatchRationale {
                version: "2.0.0".to_string(),
                policy_version: "2.1.0".to_string(),
                reason_codes: vec![
                    "WEIGHTED_FAIRNESS".to_string(),
                    "DEVICE_SCORE".to_string(),
                ],
                selected_backend: "sim:local".to_string(),
                selected_queue: "default".to_string(),
                attributes: std::collections::HashMap::from([
                    ("policy_branch".to_string(), "baseline".to_string()),
                    (
                        "fallback_reason".to_string(),
                        "deterministic fixture".to_string(),
                    ),
                ]),
                timeline_ref: format!("qfs://jobs/{}/timeline.json", job_id),
                logs_ref: format!("qfs://jobs/{}/logs/dispatch.log", job_id),
                trace_id: "trace-demo".to_string(),
                trace_ref: "trace://trace-demo".to_string(),
                ..Default::default()
            }),
        }))
    }
}

fn map_transport_error(err: TransportError) -> GrpcLikeError {
    GrpcLikeError {
        code: GrpcCode::Unavailable,
        message: format!("failed to connect to system api: {err}"),
        retry_hint: None,
    }
}

fn map_status_error(status: tonic::Status) -> GrpcLikeError {
    let code = match status.code() {
        tonic::Code::InvalidArgument => GrpcCode::InvalidArgument,
        tonic::Code::NotFound => GrpcCode::NotFound,
        tonic::Code::FailedPrecondition => GrpcCode::FailedPrecondition,
        tonic::Code::Unavailable => GrpcCode::Unavailable,
        tonic::Code::DeadlineExceeded => GrpcCode::DeadlineExceeded,
        _ => GrpcCode::Internal,
    };
    GrpcLikeError {
        code,
        message: status.message().to_string(),
        retry_hint: None,
    }
}

fn map_job_state(state: i32) -> String {
    match state {
        1 => "PENDING",
        2 => "COMPILING",
        3 => "QUEUED",
        4 => "RUNNING",
        5 => "DONE",
        6 => "ERROR",
        7 => "CANCELLED",
        8 => "TIMEOUT",
        _ => "UNSPECIFIED",
    }
    .to_string()
}

fn connect_client(
) -> Result<eigen::api::v1::job_service_client::JobServiceClient<Channel>, GrpcLikeError> {
    let endpoint = Endpoint::from_shared(system_api_endpoint()).map_err(|e| GrpcLikeError {
        code: GrpcCode::InvalidArgument,
        message: format!("invalid system api endpoint: {e}"),
        retry_hint: None,
    })?;
    let client = block_on_result(async {
        endpoint
            .connect()
            .await
            .map(eigen::api::v1::job_service_client::JobServiceClient::new)
            .map_err(map_transport_error)
    })?;
    Ok(client)
}

fn build_api_envelope(
    req: &SubmitJobRequest,
    options: &PublicSubmitOptions,
) -> eigen::api::v1::ApiRequestEnvelope {
    let envelope = normalized_public_submit_envelope(req, options);
    eigen::api::v1::ApiRequestEnvelope {
        contract_version: envelope.contract_version,
        request_id: envelope.request_id,
        idempotency_key: envelope.idempotency_key,
        traceparent: envelope.traceparent,
        tenant_id: envelope.tenant_id,
        project_id: envelope.project_id,
        client_version: envelope.client_version,
        deadline: None,
    }
}

fn workload_to_proto(workload: &WorkloadContract) -> eigen::api::v1::WorkloadContract {
    let kind = match workload.kind.as_str() {
        "QuantumJob" => 1,
        "HybridWorkflow" => 2,
        "DistributedJob" => 3,
        "BenchmarkJob" => 4,
        "PipelineJob" => 5,
        "ReplayJob" => 6,
        _ => 1,
    };
    eigen::api::v1::WorkloadContract {
        kind,
        execution_profile: workload.execution_profile.clone(),
        replayable: workload.replayable,
    }
}

fn build_submit_proto_request(
    req: &SubmitJobRequest,
    options: &PublicSubmitOptions,
) -> eigen::api::v1::SubmitJobRequest {
    let program = match &req.program {
        ProgramSource::EigenLangSource {
            source,
            entrypoint,
            sha256,
        } => Some(eigen::api::v1::submit_job_request::Program::EigenLang(
            eigen::api::v1::EigenLangSource {
                source: source.as_bytes().to_vec(),
                entrypoint: entrypoint.clone(),
                sha256: sha256.clone(),
            },
        )),
    };

    eigen::api::v1::SubmitJobRequest {
        envelope: Some(build_api_envelope(req, options)),
        name: req.name.clone(),
        program,
        target: req.target.clone(),
        priority: req.priority,
        compiler_options: req.compiler_options.clone().into_iter().collect::<HashMap<_, _>>(),
        metadata: req.metadata.clone().into_iter().collect::<HashMap<_, _>>(),
        dependencies: req.dependencies.clone(),
        workload: Some(workload_to_proto(&req.workload)),
        tenant: None,
        reservation_id: String::new(),
    }
}

pub fn submit_job_to_system_api(
    req: &SubmitJobRequest,
    options: &PublicSubmitOptions,
) -> Result<SubmitJobResponse, GrpcLikeError> {
    let _ = validate_submit_request_against_system_api_schema(req);
    block_on_result(async {
        let mut client = connect_client()?;
        let proto_req = build_submit_proto_request(req, options);
        let resp = client
            .submit_job(proto_req)
            .await
            .map_err(map_status_error)?
            .into_inner();
        Ok(SubmitJobResponse {
            job_id: resp.job_id,
        })
    })
}

pub fn validate_submit_request_against_system_api_schema(
    req: &SubmitJobRequest,
) -> Result<(), JobSpecValidationError> {
    let mut violations = Vec::new();
    if req.name.trim().is_empty() {
        violations.push(FieldViolation {
            field: "name".to_string(),
            description: "field is required".to_string(),
        });
    }
    if req.target.trim().is_empty() {
        violations.push(FieldViolation {
            field: "target".to_string(),
            description: "field is required".to_string(),
        });
    }

    let ProgramSource::EigenLangSource {
        source,
        entrypoint,
        sha256,
    } = &req.program;
    if source.trim().is_empty() {
        violations.push(FieldViolation {
            field: "program.eigen_lang_source.source".to_string(),
            description: "field is required".to_string(),
        });
    }
    if entrypoint.trim().is_empty() {
        violations.push(FieldViolation {
            field: "program.eigen_lang_source.entrypoint".to_string(),
            description: "field is required".to_string(),
        });
    }
    if sha256.len() != 64 || !sha256.chars().all(|c| c.is_ascii_hexdigit()) {
        violations.push(FieldViolation {
            field: "program.eigen_lang_source.sha256".to_string(),
            description: "must be 64-char lowercase hex sha256".to_string(),
        });
    }

    if violations.is_empty() { Ok(()) } else { Err(JobSpecValidationError::new(violations)) }
}

pub fn normalized_public_submit_envelope(
    req: &SubmitJobRequest,
    options: &PublicSubmitOptions,
) -> PublicSubmitEnvelope {
    let canonical_digest = canonical_jobspec_digest_from_request(req, &req.jobspec_api_version);
    let request_id = options
        .request_id
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .map(str::to_string)
        .unwrap_or_else(|| format!("req_{}", &canonical_digest[0..16]));
    let idempotency_key = options
        .idempotency_key
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .map(str::to_string)
        .unwrap_or_else(|| format!("idem_{}", &canonical_digest[0..32]));

    PublicSubmitEnvelope {
        contract_version: PUBLIC_ENVELOPE_CONTRACT_VERSION.to_string(),
        request_id,
        idempotency_key,
        traceparent: options.traceparent.clone().unwrap_or_default(),
        tenant_id: options
            .tenant_id
            .clone()
            .unwrap_or_else(|| DEFAULT_TENANT_ID.to_string()),
        project_id: options
            .project_id
            .clone()
            .unwrap_or_else(|| DEFAULT_PROJECT_ID.to_string()),
        client_version: options
            .client_version
            .clone()
            .unwrap_or_else(|| CLI_CLIENT_VERSION.to_string()),
    }
}

pub fn build_public_submit_payload_json(
    req: &SubmitJobRequest,
    options: &PublicSubmitOptions,
) -> String {
    let envelope = normalized_public_submit_envelope(req, options);
    let canonical_jobspec = canonical_jobspec_json_from_request(req, &req.jobspec_api_version);
    let legacy_request = legacy_submit_request_body_json(req);
    format!(
        concat!(
            "{{",
            "\"envelope\":{{",
            "\"contract_version\":\"{contract_version}\",",
            "\"request_id\":\"{request_id}\",",
            "\"idempotency_key\":\"{idempotency_key}\",",
            "\"traceparent\":\"{traceparent}\",",
            "\"tenant_id\":\"{tenant_id}\",",
            "\"project_id\":\"{project_id}\",",
            "\"client_version\":\"{client_version}\"",
            "}},",
            "\"jobspec\":{canonical_jobspec},",
            "\"submit_request\":{legacy_request}",
            "}}"
        ),
        contract_version = json_escape(&envelope.contract_version),
        request_id = json_escape(&envelope.request_id),
        idempotency_key = json_escape(&envelope.idempotency_key),
        traceparent = json_escape(&envelope.traceparent),
        tenant_id = json_escape(&envelope.tenant_id),
        project_id = json_escape(&envelope.project_id),
        client_version = json_escape(&envelope.client_version),
        canonical_jobspec = canonical_jobspec,
        legacy_request = legacy_request,
    )
}

pub fn build_submit_request_envelope_json(req: &SubmitJobRequest) -> String {
    build_public_submit_payload_json(req, &PublicSubmitOptions::default())
}

fn legacy_submit_request_body_json(req: &SubmitJobRequest) -> String {
    let ProgramSource::EigenLangSource {
        source,
        entrypoint,
        sha256,
    } = &req.program;
    let escaped_name = json_escape(&req.name);
    let escaped_target = json_escape(&req.target);
    let escaped_source = json_escape(source);
    let escaped_entrypoint = json_escape(entrypoint);
    let escaped_sha256 = json_escape(sha256);

    format!(
        concat!(
            "{{",
            "\"name\":\"{name}\",",
            "\"program\":{{",
            "\"eigen_lang_source\":{{",
            "\"source\":\"{source}\",",
            "\"entrypoint\":\"{entrypoint}\",",
            "\"sha256\":\"{sha256}\"",
            "}}",
            "}},",
            "\"target\":\"{target}\"",
            "}}"
        ),
        name = escaped_name,
        source = escaped_source,
        entrypoint = escaped_entrypoint,
        sha256 = escaped_sha256,
        target = escaped_target,
    )
}

fn validate_entrypoint(source: &str, entrypoint: &str) -> Result<(), JobSpecValidationError> {
    let decorated_count = source.matches("@hybrid_program").count();
    if decorated_count != 1 {
        return Err(JobSpecValidationError::new(vec![FieldViolation {
            field: "program.eigen.py".to_string(),
            description: "must contain exactly one @hybrid_program".to_string(),
        }]));
    }

    let signature = format!("def {entrypoint}(");
    if !source.contains(&signature) {
        return Err(JobSpecValidationError::new(vec![FieldViolation {
            field: "spec.entrypoint".to_string(),
            description: format!("entrypoint '{entrypoint}' not found in source"),
        }]));
    }

    Ok(())
}

fn resolve_program_path(basedir: &Path, program_path: &str) -> PathBuf {
    let p = PathBuf::from(program_path);
    if p.is_absolute() { p } else { basedir.join(p) }
}

fn validate_safe_relative_path(program_path: &str) -> Result<(), JobSpecValidationError> {
    let p = PathBuf::from(program_path);
    if p.is_absolute()
        || p.components()
            .any(|c| matches!(c, std::path::Component::ParentDir))
    {
        return Err(JobSpecValidationError::new(vec![FieldViolation {
            field: "spec.program.path".to_string(),
            description: "path traversal is not allowed".to_string(),
        }]));
    }
    Ok(())
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    let digest = sha256(bytes);
    let mut out = String::with_capacity(64);
    for b in digest {
        out.push_str(&format!("{b:02x}"));
    }
    out
}

fn sha256(input: &[u8]) -> [u8; 32] {
    const H0: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];

    let bit_len = (input.len() as u64) * 8;
    let mut msg = input.to_vec();
    msg.push(0x80);
    while (msg.len() % 64) != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bit_len.to_be_bytes());

    let mut h = H0;
    for chunk in msg.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (i, word) in w.iter_mut().take(16).enumerate() {
            let j = i * 4;
            *word = u32::from_be_bytes([chunk[j], chunk[j + 1], chunk[j + 2], chunk[j + 3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }

        let mut a = h[0];
        let mut b = h[1];
        let mut c = h[2];
        let mut d = h[3];
        let mut e = h[4];
        let mut f = h[5];
        let mut g = h[6];
        let mut hh = h[7];

        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }

        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }

    let mut out = [0u8; 32];
    for (i, word) in h.into_iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    out
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

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GrpcCode {
    InvalidArgument,
    NotFound,
    FailedPrecondition,
    Unavailable,
    DeadlineExceeded,
    Internal,
}

impl GrpcCode {
    pub fn as_str(&self) -> &'static str {
        match self {
            GrpcCode::InvalidArgument => "INVALID_ARGUMENT",
            GrpcCode::NotFound => "NOT_FOUND",
            GrpcCode::FailedPrecondition => "FAILED_PRECONDITION",
            GrpcCode::Unavailable => "UNAVAILABLE",
            GrpcCode::DeadlineExceeded => "DEADLINE_EXCEEDED",
            GrpcCode::Internal => "INTERNAL",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GrpcLikeError {
    pub code: GrpcCode,
    pub message: String,
    pub retry_hint: Option<String>,
}

impl Display for GrpcLikeError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.code.as_str(), self.message)
    }
}

impl std::error::Error for GrpcLikeError {}

#[derive(Debug, Clone, PartialEq)]
pub struct JobStatusView {
    pub job_id: String,
    pub state: String,
    pub stage: String,
    pub progress: f32,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct JobUpdateView {
    pub event_seq: u64,
    pub state: String,
    pub stage: String,
    pub progress: f32,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobResultsView {
    pub job_id: String,
    pub state: String,
    pub counts: BTreeMap<String, i64>,
    pub metadata: BTreeMap<String, String>,
    pub error_code: Option<String>,
    pub error_summary: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DispatchRationaleView {
    pub version: String,
    pub policy_version: String,
    pub reason_codes: Vec<String>,
    pub selected_backend: String,
    pub selected_queue: String,
    pub timeline_ref: String,
    pub logs_ref: String,
    pub trace_id: Option<String>,
    pub trace_ref: Option<String>,
}

pub fn compile_job_to_aqo_json(job_path: &Path) -> Result<String, SubmitBuildError> {
    let req = build_submit_request_from_job_file(job_path)?;
    let (runtime_hints, execution_annotations) =
        runtime_intelligence_hints_for_compile(&req).map_err(SubmitBuildError::Validation)?;
    let ProgramSource::EigenLangSource {
        source,
        entrypoint,
        sha256,
    } = req.program;
    let escaped_entrypoint = json_escape(&entrypoint);
    let escaped_target = json_escape(&req.target);

    Ok(format!(
        concat!(
            "{{\n",
            "  \"aqo_version\": \"0.1\",\n",
            "  \"source_lang\": \"eigen-lang\",\n",
            "  \"entrypoint\": \"{escaped_entrypoint}\",\n",
            "  \"target\": \"{escaped_target}\",\n",
            "  \"program_sha256\": \"{sha256}\",\n",
            "  \"source_bytes\": {source_bytes},\n",
            "  \"operations\": [],\n",
            "  \"metadata\": {{\n",
            "    \"compiled_by\": \"eigen-cli-local\",\n",
            "    \"runtime_intelligence_hints\": {runtime_hints},\n",
            "    \"execution_annotations\": {execution_annotations}\n",
            "  }}\n",
            "}}"
        ),
        escaped_entrypoint = escaped_entrypoint,
        escaped_target = escaped_target,
        sha256 = sha256,
        source_bytes = source.len(),
        runtime_hints = runtime_hints,
        execution_annotations = execution_annotations,
    ))
}

fn runtime_intelligence_hints_for_compile(
    req: &SubmitJobRequest,
) -> Result<(String, String), JobSpecValidationError> {
    let mut violations = Vec::new();
    let target = req.target.trim();
    if !is_supported_runtime_target(target) {
        violations.push(FieldViolation {
            field: "spec.target".to_string(),
            description: format!(
                "unsupported runtime target '{target}' (supported prefixes: sim:, qpu:, hw:)"
            ),
        });
    }

    let policy_from_option = req
        .compiler_options
        .get("runtime.policy")
        .map(String::as_str);
    let policy_from_metadata = req.metadata.get("runtime.policy").map(String::as_str);
    if let (Some(option_value), Some(metadata_value)) = (policy_from_option, policy_from_metadata)
        && option_value != metadata_value
    {
        violations.push(FieldViolation {
            field: "spec.compiler_options.runtime.policy".to_string(),
            description: format!(
                "policy conflict with spec.metadata.runtime.policy ('{option_value}' != '{metadata_value}')"
            ),
        });
    }

    if let Some(required_backend) = req.compiler_options.get("runtime.require_backend")
        && required_backend == "qpu"
        && target.starts_with("sim:")
    {
        violations.push(FieldViolation {
            field: "spec.compiler_options.runtime.require_backend".to_string(),
            description: "policy conflict: runtime.require_backend=qpu cannot target simulator"
                .to_string(),
        });
    }

    if !violations.is_empty() {
        return Err(JobSpecValidationError {
            code: "RUNTIME_INTELLIGENCE_DIAGNOSTIC",
            violations,
        });
    }

    let scoring_profile = req
        .compiler_options
        .get("runtime.scoring_profile")
        .cloned()
        .unwrap_or_else(|| "balanced".to_string());
    let preferred_backend = if target.starts_with("sim:") {
        "simulator"
    } else {
        "hardware"
    };

    let recommendation_policy = recommendation_policy_for_compile(req)?;

    let runtime_hints = format!(
        concat!(
            "{{",
            "\"version\":\"{version}\",",
            "\"diagnostics_version\":\"{diagnostics_version}\",",
            "\"target_family\":\"{target_family}\",",
            "\"preferred_backend\":\"{preferred_backend}\",",
            "\"scoring_profile\":\"{scoring_profile}\",",
            "\"explainability_ref\":\"{explainability_ref}\",",
            "\"recommendation_policy\":{recommendation_policy}",
            "}}"
        ),
        version = EIGEN_LANG_RUNTIME_HINTS_VERSION,
        diagnostics_version = EIGEN_LANG_RUNTIME_DIAGNOSTICS_VERSION,
        target_family = if target.starts_with("sim:") {
            "simulator"
        } else {
            "quantum_device"
        },
        preferred_backend = preferred_backend,
        scoring_profile = json_escape(&scoring_profile),
        explainability_ref = json_escape(&format!("explain://compile/{}/{}", req.name, req.target)),
        recommendation_policy = recommendation_policy,
    );

    let execution_annotations = format!(
        concat!(
            "{{",
            "\"version\":\"{version}\",",
            "\"explainability_id\":\"{explainability_id}\",",
            "\"traceability_key\":\"{traceability_key}\"",
            "}}"
        ),
        version = EIGEN_LANG_EXECUTION_ANNOTATIONS_VERSION,
        explainability_id = json_escape(&format!(
            "explain-{}",
            &sha256_hex(req.name.as_bytes())[0..12]
        )),

        traceability_key = json_escape(&format!("trace://compile/{}/{}", req.name, req.target)),
    );

    Ok((runtime_hints, execution_annotations))
}
        
fn recommendation_policy_for_compile(
    req: &SubmitJobRequest,
) -> Result<String, JobSpecValidationError> {
    let min_confidence = req
        .compiler_options
        .get("runtime.recommendation.min_confidence")
        .and_then(|value| value.parse::<f64>().ok())
        .unwrap_or(0.8);
    let snapshot_epoch_ms = req
        .metadata
        .get("runtime.recommendation.snapshot_epoch_ms")
        .and_then(|value| value.parse::<u64>().ok())
        .unwrap_or(0);

    let context_payload = req
        .metadata
        .get("runtime.recommendation.context")
        .or_else(|| req.compiler_options.get("runtime.recommendation.context"));

    let no_context = format!(
        "{{\"status\":\"FALLBACK\",\"reason\":\"NO_CONTEXT\",\"min_confidence\":{min_confidence:.3},\"snapshot_epoch_ms\":{snapshot_epoch_ms}}}"
    );
    let Some(payload) = context_payload else {
        return Ok(no_context);
    };

    let contract = extract_json_string_field(payload, "contract");
    let version = extract_json_string_field(payload, "version");
    let backend_class = extract_json_string_field(payload, "backend_class");
    let confidence = extract_json_number_field(payload, "confidence");
    let fallback_used = extract_json_bool_field(payload, "fallback_used");
    let expires_at_epoch_ms = extract_json_u64_field(payload, "expires_at_epoch_ms");
    if contract.as_deref() != Some("pattern_miner.recommendation")
        || version.as_deref() != Some("1.0.0")
        || backend_class.is_none()
        || confidence.is_none()
        || fallback_used.is_none()
        || expires_at_epoch_ms.is_none()
    {
        return Err(JobSpecValidationError {
            code: "RUNTIME_INTELLIGENCE_DIAGNOSTIC",
            violations: vec![FieldViolation {
                field: "spec.metadata.runtime.recommendation.context".to_string(),
                description: "malformed recommendation context payload".to_string(),
            }],
        });
    }
    let backend_class = backend_class.expect("checked is_some");
    let confidence = confidence.expect("checked is_some");
    let fallback_used = fallback_used.expect("checked is_some");
    let expires_at_epoch_ms = expires_at_epoch_ms.expect("checked is_some");

    let fallback_reason = if fallback_used {
        Some("UPSTREAM_FALLBACK_USED")
    } else if confidence < min_confidence {
        Some("LOW_CONFIDENCE")
    } else if snapshot_epoch_ms > 0 && expires_at_epoch_ms < snapshot_epoch_ms {
        Some("STALE_CONTEXT")
    } else if req.target.starts_with("sim:") && backend_class != "sim" {
        Some("CONFLICT_TARGET_BACKEND")
    } else {
        None
    };

    if let Some(reason) = fallback_reason {
        Ok(format!(
            "{{\"status\":\"FALLBACK\",\"reason\":\"{reason}\",\"min_confidence\":{min_confidence:.3},\"snapshot_epoch_ms\":{snapshot_epoch_ms}}}"
        ))
    } else {
        Ok(format!(
            "{{\"status\":\"APPLIED\",\"reason\":\"NONE\",\"backend_class\":\"{}\",\"confidence\":{confidence:.6},\"snapshot_epoch_ms\":{snapshot_epoch_ms}}}",
            json_escape(&backend_class)
        ))
    }
}

fn is_supported_runtime_target(target: &str) -> bool {
    target.starts_with("sim:") || target.starts_with("qpu:") || target.starts_with("hw:")
}

pub fn visualize_aqo_json(aqo_json: &str) -> String {
    let sha = extract_json_string_field(aqo_json, "program_sha256")
        .unwrap_or_else(|| "unknown".to_string());
    let target =
        extract_json_string_field(aqo_json, "target").unwrap_or_else(|| "unknown".to_string());
    let entrypoint =
        extract_json_string_field(aqo_json, "entrypoint").unwrap_or_else(|| "unknown".to_string());

    format!(
        concat!(
            "AQO Graph (MVP)\n",
            "  target: {target}\n",
            "  entrypoint: {entrypoint}\n",
            "  program_sha256: {sha}\n",
            "\n",
            "  [START] -> [COMPILE] -> [EXECUTE] -> [MEASURE]\n"
        ),
        target = target,
        entrypoint = entrypoint,
        sha = sha
    )
}

fn json_escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for ch in value.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(ch),
        }
    }
    out
}

fn extract_json_string_field(doc: &str, field: &str) -> Option<String> {
    let needle = format!("\"{field}\"");
    let start = doc.find(&needle)?;
    let tail = &doc[start + needle.len()..];
    let quote = tail.find('"')?;
    let tail = &tail[quote + 1..];
    let end = tail.find('"')?;
    Some(tail[..end].to_string())
}

fn extract_json_bool_field(doc: &str, field: &str) -> Option<bool> {
    let needle = format!("\"{field}\"");
    let start = doc.find(&needle)?;
    let tail = &doc[start + needle.len()..];
    let colon = tail.find(':')?;
    let value = tail[colon + 1..]
        .trim_start()
        .strip_prefix("true")
        .map(|_| true)
        .or_else(|| {
            tail[colon + 1..]
                .trim_start()
                .strip_prefix("false")
                .map(|_| false)
        })?;
    Some(value)
}

fn extract_json_number_field(doc: &str, field: &str) -> Option<f64> {
    let needle = format!("\"{field}\"");
    let start = doc.find(&needle)?;
    let tail = &doc[start + needle.len()..];
    let colon = tail.find(':')?;
    let value = tail[colon + 1..].trim_start();
    let end = value.find([',', '}']).unwrap_or(value.len());
    value[..end].trim().parse::<f64>().ok()
}

fn extract_json_u64_field(doc: &str, field: &str) -> Option<u64> {
    extract_json_number_field(doc, field).map(|v| v as u64)
}

pub fn get_job_status_from_system_api(job_id: &str) -> Result<JobStatusView, GrpcLikeError> {
    if job_id.trim().is_empty() {
        return Err(GrpcLikeError {
            code: GrpcCode::InvalidArgument,
            message: "job_id is required".to_string(),
            retry_hint: None,
        });
    }

    block_on_result(async {
        let mut client = connect_client()?;
        let resp = client
            .get_job_status(eigen::api::v1::GetJobStatusRequest {
                envelope: None,
                job_id: job_id.to_string(),
            })
            .await
            .map_err(map_status_error)?
            .into_inner();
        let status = resp.status.ok_or_else(|| GrpcLikeError {
            code: GrpcCode::Internal,
            message: "empty GetJobStatus response".to_string(),
            retry_hint: None,
        })?;
        Ok(JobStatusView {
            job_id: status.job_id,
            state: map_job_state(status.state),
            stage: status.stage,
            progress: status.progress,
            message: status.message,
        })
    })
}

pub fn stream_job_updates_from_system_api(
    job_id: &str,
) -> Result<Vec<JobUpdateView>, GrpcLikeError> {
    block_on_result(async {
        let mut client = connect_client()?;
        let mut stream = client
            .stream_job_updates(eigen::api::v1::StreamJobUpdatesRequest {
                envelope: None,
                job_id: job_id.to_string(),
                last_event_seq: 0,
            })
            .await
            .map_err(map_status_error)?
            .into_inner();
        let mut updates = Vec::new();
        while let Some(item) = stream.message().await.map_err(map_status_error)? {
            let Some(update) = item.update else {
                continue;
            };
            updates.push(JobUpdateView {
                event_seq: update.event_seq,
                state: map_job_state(update.state),
                stage: update.stage,
                progress: update.progress,
                message: update.message,
            });
        }
        Ok(updates)
    })
}

pub fn get_job_results_from_system_api(job_id: &str) -> Result<JobResultsView, GrpcLikeError> {
    if job_id.trim().is_empty() {
        return Err(GrpcLikeError {
            code: GrpcCode::InvalidArgument,
            message: "job_id is required".to_string(),
            retry_hint: None,
        });
    }

    block_on_result(async {
    let mut client = connect_client()?;
    let resp = client
        .get_job_results(eigen::api::v1::GetJobResultsRequest {
            envelope: None,
            job_id: job_id.to_string(),
        })
        .await
        .map_err(map_status_error)?
        .into_inner();

    let mut counts = BTreeMap::new();
        for (k, v) in resp.counts {
            counts.insert(k, v);
        }

    let mut metadata = BTreeMap::new();
        for (k, v) in resp.metadata {
            metadata.insert(k, v);
        }

    Ok(JobResultsView {
        job_id: resp.job_id,
        state: map_job_state(resp.state),
        counts,
        metadata,
        error_code: if resp.error_code.is_empty() {
            None
        } else {
            Some(resp.error_code)
        },
        error_summary: if resp.error_summary.is_empty() {
            None
        } else {
            Some(resp.error_summary)
        },
    })
})
}

pub fn get_dispatch_rationale_from_system_api(
    job_id: &str,
) -> Result<DispatchRationaleView, GrpcLikeError> {
    if job_id.trim().is_empty() {
        return Err(GrpcLikeError {
            code: GrpcCode::InvalidArgument,
            message: "job_id is required".to_string(),
            retry_hint: None,
        });
    }
    block_on_result(async {
        let mut client = connect_client()?;
        let resp = client
            .get_dispatch_rationale(eigen::api::v1::GetDispatchRationaleRequest {
                envelope: None,
                job_id: job_id.to_string(),
            })
            .await
            .map_err(map_status_error)?
            .into_inner();
        let rationale = resp.rationale.ok_or_else(|| GrpcLikeError {
            code: GrpcCode::Internal,
            message: "empty GetDispatchRationale response".to_string(),
            retry_hint: None,
        })?;
        Ok(DispatchRationaleView {
            version: rationale.version,
            policy_version: rationale.policy_version,
            reason_codes: rationale.reason_codes,
            selected_backend: rationale.selected_backend,
            selected_queue: rationale.selected_queue,
            timeline_ref: rationale.timeline_ref,
            logs_ref: rationale.logs_ref,
            trace_id: if rationale.trace_id.is_empty() { None } else { Some(rationale.trace_id) },
            trace_ref: if rationale.trace_ref.is_empty() { None } else { Some(rationale.trace_ref) },
        })
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_dir() -> PathBuf {
        let mut dir = std::env::temp_dir();
        dir.push(format!("eigen-cli-tests-{}", std::process::id()));
        dir.push(format!(
            "{}",
            sha256_hex(format!("{}", rand_seed()).as_bytes())
        ));
        fs::create_dir_all(&dir).expect("temp dir");
        dir
    }

    fn rand_seed() -> u128 {
        use std::time::{SystemTime, UNIX_EPOCH};
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos()
    }

    #[test]
    fn yaml_parsing_supports_program_path_and_entrypoint() {
        let yaml = r#"
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: test
spec:
  program_path: custom.eigen.py
  entrypoint: run
  target: sim:local
"#;
        let spec = parse_and_validate_jobspec(yaml).expect("valid");
        assert_eq!(spec.spec.program_path, Some("custom.eigen.py".to_string()));
        assert_eq!(spec.spec.entrypoint, "run");
    }

    #[test]
    fn file_discovery_defaults_to_program_eigen_py() {
        let dir = temp_dir();
        fs::write(
            dir.join("job.yaml"),
            r#"
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: bell
spec:
  target: sim:local
"#,
        )
        .unwrap();
        fs::write(
            dir.join("program.eigen.py"),
            "@hybrid_program\ndef main():\n    return 1\n",
        )
        .unwrap();

        let req = build_submit_request_from_job_file(&dir.join("job.yaml")).expect("request");
        let ProgramSource::EigenLangSource { entrypoint, .. } = req.program;
        assert_eq!(entrypoint, "main");
    }

    #[test]
    fn hashing_is_deterministic_sha256() {
        let got = sha256_hex(b"abc");
        assert_eq!(
            got,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn request_construction_includes_sha_and_metadata() {
        let dir = temp_dir();
        fs::write(
            dir.join("job.yaml"),
            r#"
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: bell
spec:
  program_path: src/program.eigen.py
  target: sim:local
  metadata:
    shots: "100"
"#,
        )
        .unwrap();
        fs::create_dir_all(dir.join("src")).unwrap();
        fs::write(
            dir.join("src/program.eigen.py"),
            "@hybrid_program\ndef main():\n    return 1\n",
        )
        .unwrap();

        let req = build_submit_request_from_job_file(&dir.join("job.yaml")).expect("request");
        let ProgramSource::EigenLangSource {
            entrypoint, sha256, ..
        } = req.program;
        assert_eq!(entrypoint, "main");
        assert_eq!(req.metadata.get("source_sha256"), Some(&sha256));
    }

    #[test]
    fn inline_program_is_accepted_for_public_submission_conformance() {
        let yaml = r#"
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: test
spec:
  program: |
    @hybrid_program
    def main():
        return 1
  target: sim:local
"#;
        let spec = parse_and_validate_jobspec(yaml).unwrap();
        let req = map_to_submit_job_request_with_packaging(&spec, Path::new(".")).unwrap();
        assert_eq!(req.jobspec_api_version, LEGACY_JOBSPEC_API_VERSION);
        let ProgramSource::EigenLangSource { source, .. } = req.program;
        assert!(source.contains("@hybrid_program"));
    }

    #[test]
    fn jobspec_v1_nested_program_path_is_supported() {
        let yaml = r#"
apiVersion: eigen.os/v1
kind: QuantumJob
metadata:
  name: test
spec:
  program:
    path: custom.eigen.py
  entrypoint: run
  target: sim:local
"#;
        let spec = parse_and_validate_jobspec(yaml).expect("valid");
        assert_eq!(spec.spec.program_path, Some("custom.eigen.py".to_string()));
        assert_eq!(spec.spec.entrypoint, "run");
    }

    #[test]
    fn canonical_jobspec_digest_from_request_is_deterministic() {
        let req = SubmitJobRequest {
            jobspec_api_version: JOBSPEC_API_VERSION.to_string(),
            name: "bell".to_string(),
            program: ProgramSource::EigenLangSource {
                source: "@hybrid_program\ndef main():\n    return 1\n".to_string(),
                entrypoint: "main".to_string(),
                sha256: sha256_hex(b"@hybrid_program\ndef main():\n    return 1\n"),
            },
            target: "sim:local".to_string(),
            priority: 50,
            compiler_options: BTreeMap::new(),
            metadata: BTreeMap::new(),
            dependencies: Vec::new(),
            workload: default_workload_contract(),
        };
        let first = canonical_jobspec_digest_from_request(&req, JOBSPEC_API_VERSION);
        let second = canonical_jobspec_digest_from_request(&req, JOBSPEC_API_VERSION);
        let canonical = canonical_jobspec_json_from_request(&req, JOBSPEC_API_VERSION);
        assert_eq!(first, second);
        assert_eq!(first.len(), 64);
        assert!(canonical.contains("\"version\":\"1.0.0\""));
        assert!(canonical.contains("\"apiVersion\":\"eigen.os/v1\""));
    }

    #[test]
    fn public_submit_payload_normalizes_minimal_inline_reference_fixture() {
        let repo = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../..");
        let yaml =
            fs::read_to_string(repo.join("docs/reference/fixtures/jobspec/1.0/minimal/job.yaml"))
                .expect("minimal fixture");
        let spec = parse_and_validate_jobspec(&yaml).expect("valid fixture");
        let req = map_to_submit_job_request_with_packaging(&spec, Path::new(".")).expect("request");
        let payload = build_public_submit_payload_json(
            &req,
            &PublicSubmitOptions {
                traceparent: Some(
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01".to_string(),
                ),
                ..PublicSubmitOptions::default()
            },
        );

        assert!(payload.contains("\"envelope\""));
        assert!(payload.contains("\"contract_version\":\"1.0.0\""));
        assert!(payload.contains("\"idempotency_key\":\"idem_"));
        assert!(payload.contains(
            "\"traceparent\":\"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01\""
        ));
        assert!(payload.contains("\"contract\":\"jobspec.normalized\""));
        assert!(payload.contains("\"apiVersion\":\"eigen.os/v1\""));
        assert!(payload.contains("\"name\":\"v1-minimal\""));
    }

    #[test]
    fn public_submit_payload_normalizes_full_file_reference_fixture() {
        let repo = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../..");
        let dir = temp_dir();
        fs::write(
            dir.join("job.yaml"),
            fs::read_to_string(repo.join("docs/reference/fixtures/jobspec/1.0/full/job.yaml"))
                .expect("full fixture"),
        )
        .unwrap();
        fs::write(
            dir.join("program.eigen.py"),
            "@hybrid_program\ndef run():\n    return 2\n",
        )
        .unwrap();

        let req = build_submit_request_from_job_file(&dir.join("job.yaml")).expect("request");
        let payload = build_public_submit_payload_json(
            &req,
            &PublicSubmitOptions {
                request_id: Some("req-explicit".to_string()),
                idempotency_key: Some("idem-explicit".to_string()),
                tenant_id: Some("tenant-a".to_string()),
                project_id: Some("project-a".to_string()),
                ..PublicSubmitOptions::default()
            },
        );

        assert!(payload.contains("\"request_id\":\"req-explicit\""));
        assert!(payload.contains("\"idempotency_key\":\"idem-explicit\""));
        assert!(payload.contains("\"tenant_id\":\"tenant-a\""));
        assert!(payload.contains("\"project_id\":\"project-a\""));
        assert!(payload.contains("\"name\":\"v1-full\""));
        assert!(payload.contains("\"entrypoint\":\"run\""));
        assert!(payload.contains("\"optimization_level\":\"2\""));
        assert!(payload.contains("qfs://datasets/h2.json"));
    }

    #[test]
    fn status_watch_results_workflow_views_are_consistent() {
        let status = get_job_status_from_system_api("job-demo").expect("status");
        assert_eq!(status.state, "RUNNING");

        let updates = stream_job_updates_from_system_api("job-demo").expect("updates");
        assert_eq!(updates.last().map(|u| u.state.clone()), Some("DONE".to_string()));

        let results = get_job_results_from_system_api("job-demo-done").expect("results");
        assert_eq!(results.state, "DONE");
        assert_eq!(results.counts.get("00"), Some(&512));
    }

    #[test]
    fn results_error_state_contains_error_fields() {
        let results = get_job_results_from_system_api("job-demo-error").expect("results");
        assert_eq!(results.state, "ERROR");
        assert_eq!(results.error_code.as_deref(), Some("EIGEN_SIM_ERROR"));
        assert!(results.error_summary.unwrap_or_default().contains("failed"));
        assert_eq!(
            results.metadata.get("qfs_result_ref").map(String::as_str),
            Some("qfs://jobs/job-demo-error/results.parquet")
        );
    }

    #[test]
    fn results_expose_qfs_result_ref_via_metadata() {
        let results = get_job_results_from_system_api("job-demo-done").expect("results");
        assert_eq!(
            results.metadata.get("qfs_result_ref").map(String::as_str),
            Some("qfs://jobs/job-demo-done/results.parquet")
        );
    }

    #[test]
    fn local_compile_and_visualize_generate_expected_markers() {
        let dir = temp_dir();
        let yaml_path = dir.join("job.yaml");
        let program_path = dir.join("program.eigen.py");
        fs::write(
            &program_path,
            "@hybrid_program\ndef main():\n    return [('RX', 0.5, 0), ('MEASURE', 0)]\n",
        )
        .expect("program");
        fs::write(
            &yaml_path,
            format!(
                "apiVersion: eigen.os/v0.1\nkind: QuantumJob\nmetadata:\n  name: compile-test\nspec:\n  program_path: program.eigen.py\n  target: sim:local\n"
            ),
        )
        .expect("yaml");

        let aqo = compile_job_to_aqo_json(&yaml_path).expect("compile");
        assert!(aqo.contains("\"aqo_version\": \"0.1\""));
        assert!(aqo.contains("\"runtime_intelligence_hints\":"));
        assert!(aqo.contains("\"version\":\"1.1.0\""));
        assert!(aqo.contains("\"recommendation_policy\":"));
        assert!(aqo.contains("\"execution_annotations\":"));
        assert!(aqo.contains("\"explainability_id\":"));
        let viz = visualize_aqo_json(&aqo);
        assert!(viz.contains("AQO Graph (MVP)"));
        assert!(viz.contains("program_sha256:"));
    }
    
    #[test]
    fn compile_rejects_unsupported_runtime_target_deterministically() {
        let dir = temp_dir();
        let yaml_path = dir.join("job.yaml");
        fs::write(
            dir.join("program.eigen.py"),
            "@hybrid_program\ndef main():\n    return 1\n",
        )
        .unwrap();
        fs::write(
            &yaml_path,
            "apiVersion: eigen.os/v0.1\nkind: QuantumJob\nmetadata:\n  name: bad-target\nspec:\n  target: edge:gpu\n",
        )
        .unwrap();

        let err = compile_job_to_aqo_json(&yaml_path).unwrap_err();
        match err {
            SubmitBuildError::Validation(validation) => {
                assert_eq!(validation.code, "RUNTIME_INTELLIGENCE_DIAGNOSTIC");
                assert_eq!(
                    validation.violations[0].description,
                    "unsupported runtime target 'edge:gpu' (supported prefixes: sim:, qpu:, hw:)"
                );
            }
            other => panic!("expected validation error, got {other:?}"),
        }
    }

    #[test]
    fn compile_rejects_policy_conflicts_deterministically() {
        let dir = temp_dir();
        let yaml_path = dir.join("job.yaml");
        fs::write(
            dir.join("program.eigen.py"),
            "@hybrid_program\ndef main():\n    return 1\n",
        )
        .unwrap();
        fs::write(
            &yaml_path,
            "apiVersion: eigen.os/v0.1\nkind: QuantumJob\nmetadata:\n  name: policy-clash\nspec:\n  target: sim:local\n  compiler_options:\n    runtime.policy: latency\n    runtime.require_backend: qpu\n  metadata:\n    runtime.policy: throughput\n",
        )
        .unwrap();

        let err = compile_job_to_aqo_json(&yaml_path).unwrap_err();
        match err {
            SubmitBuildError::Validation(validation) => {
                assert_eq!(validation.code, "RUNTIME_INTELLIGENCE_DIAGNOSTIC");
                assert_eq!(validation.violations.len(), 2);
                assert!(validation.violations.iter().any(|v| {
                    v.description
                        .contains("policy conflict with spec.metadata.runtime.policy")
                }));
                assert!(validation.violations.iter().any(|v| {
                    v.description
                        .contains("runtime.require_backend=qpu cannot target simulator")
                }));
            }
            other => panic!("expected validation error, got {other:?}"),
        }
    }

    #[test]
    fn compile_recommendation_policy_fallback_variants_are_deterministic() {
        let dir = temp_dir();
        let yaml_path = dir.join("job.yaml");
        fs::write(
            dir.join("program.eigen.py"),
            "@hybrid_program\ndef main():\n    return 1\n",
        )
        .unwrap();
        fs::write(
            &yaml_path,
            "apiVersion: eigen.os/v0.1\nkind: QuantumJob\nmetadata:\n  name: rec-policy\nspec:\n  target: sim:local\n",
        )
        .unwrap();
        let no_context = compile_job_to_aqo_json(&yaml_path).unwrap();
        assert!(no_context.contains("\"reason\":\"NO_CONTEXT\""));

        fs::write(
            &yaml_path,
            "apiVersion: eigen.os/v0.1\nkind: QuantumJob\nmetadata:\n  name: rec-policy\nspec:\n  target: sim:local\n  metadata:\n    runtime.recommendation.snapshot_epoch_ms: \"200\"\n    runtime.recommendation.context: '{\"contract\":\"pattern_miner.recommendation\",\"version\":\"1.0.0\",\"backend_class\":\"sim\",\"confidence\":0.99,\"fallback_used\":false,\"expires_at_epoch_ms\":100}'\n",
        )
        .unwrap();
        let stale_context = compile_job_to_aqo_json(&yaml_path).unwrap();
        assert!(stale_context.contains("\"reason\":\"STALE_CONTEXT\""));

        fs::write(
            &yaml_path,
            "apiVersion: eigen.os/v0.1\nkind: QuantumJob\nmetadata:\n  name: rec-policy\nspec:\n  target: sim:local\n  metadata:\n    runtime.recommendation.snapshot_epoch_ms: \"100\"\n    runtime.recommendation.context: '{\"contract\":\"pattern_miner.recommendation\",\"version\":\"1.0.0\",\"backend_class\":\"qpu\",\"confidence\":0.99,\"fallback_used\":false,\"expires_at_epoch_ms\":300}'\n",
        )
        .unwrap();
        let conflict_context = compile_job_to_aqo_json(&yaml_path).unwrap();
        assert!(conflict_context.contains("\"reason\":\"CONFLICT_TARGET_BACKEND\""));
    }

    #[test]
    fn compile_fails_closed_for_malformed_recommendation_context_payload() {
        let dir = temp_dir();
        let yaml_path = dir.join("job.yaml");
        fs::write(
            dir.join("program.eigen.py"),
            "@hybrid_program\ndef main():\n    return 1\n",
        )
        .unwrap();
        fs::write(
            &yaml_path,
            "apiVersion: eigen.os/v0.1\nkind: QuantumJob\nmetadata:\n  name: malformed-rec\nspec:\n  target: sim:local\n  metadata:\n    runtime.recommendation.context: '{\"contract\":\"pattern_miner.recommendation\"}'\n",
        )
        .unwrap();

        let err = compile_job_to_aqo_json(&yaml_path).unwrap_err();
        match err {
            SubmitBuildError::Validation(validation) => {
                assert_eq!(validation.code, "RUNTIME_INTELLIGENCE_DIAGNOSTIC");
                assert!(validation.violations.iter().any(|v| {
                    v.field == "spec.metadata.runtime.recommendation.context"
                        && v.description
                            .contains("malformed recommendation context payload")
                }));
            }
            other => panic!("expected validation error, got {other:?}"),
        }
    }

    #[test]
    fn dispatch_rationale_contains_version_and_reason_codes() {
        let rationale = get_dispatch_rationale_from_system_api("job-demo").expect("rationale");
        assert_eq!(rationale.version, "2.0.0");
        assert_eq!(rationale.policy_version, "2.1.0");
        assert!(rationale.reason_codes.contains(&"WEIGHTED_FAIRNESS".to_string()));
        assert!(rationale.reason_codes.contains(&"DEVICE_SCORE".to_string()));
        assert!(rationale.timeline_ref.ends_with("/timeline.json"));
    }

    #[test]
    fn client_side_schema_validation_rejects_invalid_submit_request() {
        let req = SubmitJobRequest {
            jobspec_api_version: JOBSPEC_API_VERSION.to_string(),
            name: "".to_string(),
            program: ProgramSource::EigenLangSource {
                source: "".to_string(),
                entrypoint: "".to_string(),
                sha256: "abc".to_string(),
            },
            target: "".to_string(),
            priority: 50,
            compiler_options: BTreeMap::new(),
            metadata: BTreeMap::new(),
            dependencies: Vec::new(),
            workload: default_workload_contract(),
        };

        let err = validate_submit_request_against_system_api_schema(&req).unwrap_err();
        assert!(err.violations.iter().any(|v| v.field == "name"));
        assert!(err.violations.iter().any(|v| v.field == "target"));
        assert!(
            err.violations
                .iter()
                .any(|v| v.field == "program.eigen_lang_source.sha256")
        );
    }

    #[test]
    fn request_envelope_json_matches_expected_contract_shape() {
        let req = SubmitJobRequest {
            jobspec_api_version: JOBSPEC_API_VERSION.to_string(),
            name: "bell".to_string(),
            program: ProgramSource::EigenLangSource {
                source: "@hybrid_program\ndef main():\n    pass\n".to_string(),
                entrypoint: "main".to_string(),
                sha256: "3ac225168df54212a25f4e3f8f7f9fef26f7f2f5de6d9d0bc00f7a5a9bc4d3b6"
                    .to_string(),
            },
            target: "sim:local".to_string(),
            priority: 10,
            compiler_options: BTreeMap::new(),
            metadata: BTreeMap::new(),
            dependencies: Vec::new(),
            workload: default_workload_contract(),
        };
        let envelope = build_submit_request_envelope_json(&req);
        assert!(envelope.contains("\"name\":\"bell\""));
        assert!(envelope.contains("\"eigen_lang_source\""));
        assert!(envelope.contains("\"entrypoint\":\"main\""));
        assert!(envelope.contains("\"target\":\"sim:local\""));
    }
}

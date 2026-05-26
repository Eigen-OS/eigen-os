//! Eigen CLI - MVP.

mod jobspec;

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use std::time::Duration;

const EXIT_USER_ERROR: i32 = 2;
const EXIT_NETWORK_ERROR: i32 = 3;
const EXIT_SERVER_ERROR: i32 = 4;
const PLUGIN_MANIFEST_SCHEMA_VERSION: &str = "2.1.0";
const PLUGIN_API_VERSION: &str = "2.1.0";
const EIGEN_OS_VERSION: &str = "0.6.0";
const CLI_VERSION: &str = "0.16.0";
const EIGEN_LANG_VERSION: &str = "0.1.0";
const COMPATIBILITY_MANIFEST_VERSION: &str = "1.0.0";
const COMPATIBILITY_MANIFEST_JSON: &str =
    include_str!("../tests/fixtures/plugin_compatibility_matrix_v1.json");
const BENCHMARK_RUN_CONTRACT_VERSION: &str = "1.0.0";
const BENCHMARK_RUN_SNAPSHOT_VERSION: &str = "1.0.0";
const BENCHMARK_COMPARISON_CONTRACT_VERSION: &str = "1.0.0";
const BENCHMARK_COMPARISON_VERSION: &str = "1.0.0";

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() <= 1 {
        print_help();
        std::process::exit(EXIT_USER_ERROR);
    }

    match args[1].as_str() {
        "help" | "--help" | "-h" => print_help(),
        "version" | "--version" | "-V" => println!("eigen-cli {CLI_VERSION}"),
        "plugin" => {
            if let Err(err) = run_plugin(&args[2..]) {
                eprintln!("plugin failed: {err}");
                std::process::exit(EXIT_USER_ERROR);
            }
        }
        "benchmark" => {
            if let Err(err) = run_benchmark(&args[2..]) {
                eprintln!("benchmark failed: {err}");
                std::process::exit(EXIT_USER_ERROR);
            }
        }
        "submit" => {
            if let Err(err) = run_submit(&args[2..]) {
                eprintln!("submit failed: {err}");
                std::process::exit(EXIT_USER_ERROR);
            }
        }
        "status" => {
            if let Err(code) = run_status(&args[2..]) {
                std::process::exit(code);
            }
        }
        "watch" => {
            if let Err(code) = run_watch(&args[2..]) {
                std::process::exit(code);
            }
        }
        "results" | "result" => {
            if let Err(code) = run_results(&args[2..]) {
                std::process::exit(code);
            }
        }
        "explain" => {
            if let Err(code) = run_explain(&args[2..]) {
                std::process::exit(code);
            }
        }
        "compile" => {
            if let Err(err) = run_compile(&args[2..]) {
                eprintln!("compile failed: {err}");
                std::process::exit(EXIT_USER_ERROR);
            }
        }
        "visualize" => {
            if let Err(err) = run_visualize(&args[2..]) {
                eprintln!("visualize failed: {err}");
                std::process::exit(EXIT_USER_ERROR);
            }
        }
        cmd => {
            eprintln!("Command '{cmd}' is not implemented. Use 'eigen help'.");
            std::process::exit(1);
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
struct BenchmarkRunSnapshot {
    contract_version: String,
    snapshot_version: String,
    run_id: String,
    created_at: String,
    workload: String,
    dataset: String,
    backend: String,
    seed: u64,
    metrics: BTreeMap<String, f64>,
}

#[derive(Debug, Clone, PartialEq)]
struct BenchmarkMetricComparison {
    metric: String,
    direction: String,
    baseline: f64,
    candidate: f64,
    delta: f64,
    delta_percent: f64,
    regression: bool,
}

fn run_plugin(args: &[String]) -> Result<(), String> {
    let Some(subcommand) = args.first() else {
        return Err(
            "usage: eigen plugin <scaffold|validate|package|activate> [args...]".to_string(),
        );
    };
    match subcommand.as_str() {
        "scaffold" => run_plugin_scaffold(&args[1..]),
        "validate" => run_plugin_validate(&args[1..]),
        "package" => run_plugin_package(&args[1..]),
        "activate" => run_plugin_activate(&args[1..]),
        other => Err(format!(
            "unknown plugin subcommand: {other}. expected scaffold|validate|package|activate"
        )),
    }
}

fn run_plugin_scaffold(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err(
            "usage: eigen plugin scaffold <plugin_dir> <driver|compiler_backend|optimizer|policy>"
                .to_string(),
        );
    }
    let plugin_dir = PathBuf::from(&args[0]);
    let plugin_type = &args[1];
    validate_plugin_type(plugin_type)?;
    std::fs::create_dir_all(&plugin_dir)
        .map_err(|e| format!("failed to create {}: {e}", plugin_dir.display()))?;
    let plugin_id = format!(
        "io.eigen.{}",
        plugin_dir
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("plugin")
    );
    let manifest = format!(
        "manifest_schema_version = \"{PLUGIN_MANIFEST_SCHEMA_VERSION}\"\nplugin_id = \"{plugin_id}\"\nplugin_version = \"0.1.0\"\nplugin_type = \"{plugin_type}\"\nplugin_api_version = \"{PLUGIN_API_VERSION}\"\neigen_os_compatibility = \">=0.6.0,<1.0.0\"\neigen_lang_version = \"{EIGEN_LANG_VERSION}\"\nsignature_bundle_ref = \"oci://signatures/{plugin_id}.sig\"\n\n[capabilities]\nhooks = []\n\n[policy]\nreason_codes = [\"POLICY_TIMEOUT\", \"POLICY_OUTPUT_INVALID\"]\ntimeout_ms = 500\nfallback_mode = \"deterministic_kernel\"\n"
    );
    std::fs::write(plugin_dir.join("plugin.toml"), manifest)
        .map_err(|e| format!("failed to write plugin.toml: {e}"))?;
    let readme = format!(
        "# {plugin_id}\n\nGenerated via `eigen plugin scaffold`.\n\n## Quick checks\n\n```bash\neigen plugin validate plugin.toml\n```\n"
    );
    std::fs::write(plugin_dir.join("README.md"), readme)
        .map_err(|e| format!("failed to write README.md: {e}"))?;
    let src_dir = plugin_dir.join("src");
    std::fs::create_dir_all(&src_dir)
        .map_err(|e| format!("failed to create {}: {e}", src_dir.display()))?;
    std::fs::write(
        src_dir.join("lib.rs"),
        "// Plugin entrypoint scaffold. Implement hooks declared in plugin.toml.\n",
    )
    .map_err(|e| format!("failed to write src/lib.rs: {e}"))?;
    let tests_dir = plugin_dir.join("tests");
    std::fs::create_dir_all(&tests_dir)
        .map_err(|e| format!("failed to create {}: {e}", tests_dir.display()))?;
    std::fs::write(
        tests_dir.join("manifest_contract.rs"),
        "#[test]\nfn manifest_file_exists() {\n    assert!(std::path::Path::new(\"plugin.toml\").exists());\n}\n",
    )
    .map_err(|e| format!("failed to write tests/manifest_contract.rs: {e}"))?;
    println!("scaffolded plugin at {}", plugin_dir.display());
    Ok(())
}

fn run_plugin_validate(args: &[String]) -> Result<(), String> {
    if args.len() != 1 {
        return Err("usage: eigen plugin validate <plugin.toml>".to_string());
    }
    let content =
        std::fs::read_to_string(&args[0]).map_err(|e| format!("failed to read manifest: {e}"))?;
    validate_plugin_manifest(&content)?;
    println!("manifest valid");
    Ok(())
}

fn run_plugin_package(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err("usage: eigen plugin package <plugin_dir> <output_file>".to_string());
    }
    let plugin_dir = PathBuf::from(&args[0]);
    let output = PathBuf::from(&args[1]);
    let manifest_path = plugin_dir.join("plugin.toml");
    let manifest = std::fs::read_to_string(&manifest_path)
        .map_err(|e| format!("failed to read manifest: {e}"))?;
    validate_plugin_manifest(&manifest)?;
    let payload = format!(
        "{{\"format_version\":\"1.0.0\",\"manifest\":\"{}\"}}\n",
        json_escape(&manifest.replace('\n', "\\n"))
    );
    std::fs::write(&output, payload).map_err(|e| format!("failed to write package: {e}"))?;
    println!("packaged plugin: {}", output.display());
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum PluginLifecycleState {
    Discovered,
    Registered,
    Validated,
    Active,
    Error,
    Unloaded,
}

#[derive(Debug, Clone)]
struct PluginRecord {
    plugin_id: String,
    plugin_type: String,
    plugin_api_version: String,
    eigen_os_compatibility: String,
    lifecycle_state: PluginLifecycleState,
    reason: Option<String>,
}

fn run_plugin_activate(args: &[String]) -> Result<(), String> {
    if args.is_empty() {
        return Err("usage: eigen plugin activate <plugin.toml> [plugin.toml ...]".to_string());
    }
    let manifests = args
        .iter()
        .map(|path| {
            std::fs::read_to_string(path).map_err(|e| format!("failed to read {path}: {e}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let records = activate_plugins(&manifests);
    for record in &records {
        println!(
            "{} {:?}{}",
            record.plugin_id,
            record.lifecycle_state,
            record
                .reason
                .as_ref()
                .map(|r| format!(": {r}"))
                .unwrap_or_default()
        );
    }
    if records
        .iter()
        .any(|r| r.lifecycle_state == PluginLifecycleState::Error)
    {
        return Err("plugin activation failed for one or more plugins".to_string());
    }
    Ok(())
}

fn parse_semver(version: &str) -> Option<(u64, u64, u64)> {
    let mut parts = version.split('.');
    let major = parts.next()?.parse().ok()?;
    let minor = parts.next()?.parse().ok()?;
    let patch = parts.next()?.parse().ok()?;
    if parts.next().is_some() {
        return None;
    }
    Some((major, minor, patch))
}

fn matches_range(range: &str, version: &str) -> bool {
    let Some(v) = parse_semver(version) else {
        return false;
    };
    for rule in range.split(',').map(str::trim).filter(|r| !r.is_empty()) {
        let (op, raw) = if let Some(rest) = rule.strip_prefix(">=") {
            (">=", rest)
        } else if let Some(rest) = rule.strip_prefix("<=") {
            ("<=", rest)
        } else if let Some(rest) = rule.strip_prefix(">") {
            (">", rest)
        } else if let Some(rest) = rule.strip_prefix("<") {
            ("<", rest)
        } else if let Some(rest) = rule.strip_prefix("=") {
            ("=", rest)
        } else {
            return false;
        };
        let Some(bound) = parse_semver(raw.trim()) else {
            return false;
        };
        let ok = match op {
            ">=" => v >= bound,
            "<=" => v <= bound,
            ">" => v > bound,
            "<" => v < bound,
            "=" => v == bound,
            _ => false,
        };
        if !ok {
            return false;
        }
    }
    true
}

fn evaluate_compatibility(
    plugin_api_version: &str,
    eigen_os_compatibility: &str,
    eigen_lang_version: &str,
) -> Result<(), String> {
    // compatibility tuples are sourced from a versioned machine-readable manifest fixture.
    let matrix = compatibility_tuples_from_manifest();
    let (core_major, _, _) =
        parse_semver(EIGEN_OS_VERSION).ok_or_else(|| "CORE_VERSION_INVALID".to_string())?;
    let (api_major, _, _) = parse_semver(plugin_api_version)
        .ok_or_else(|| "PLUGIN_API_VERSION_INVALID expected semver".to_string())?;
    let (lang_major, _, _) = parse_semver(eigen_lang_version)
        .ok_or_else(|| "PLUGIN_EIGEN_LANG_VERSION_INVALID expected semver".to_string())?;
    let supported = matrix.iter().any(|(c, a, l)| {
        *c == core_major.to_string() && *a == api_major.to_string() && *l == lang_major.to_string()
    });
    if !supported {
        return Err(format!(
            "PLUGIN_COMPATIBILITY_MATRIX_UNSUPPORTED core={} plugin_api={} eigen_lang={} hint=runtime->cli->plugin_api->eigen_lang remediation=upgrade_or_rebuild_against_supported_contracts",
            EIGEN_OS_VERSION, plugin_api_version, eigen_lang_version
        ));
    }
    if !matches_range(eigen_os_compatibility, EIGEN_OS_VERSION) {
        return Err(format!(
            "PLUGIN_EIGEN_OS_CONSTRAINT_MISMATCH core={} constraint={} remediation=adjust_eigen_os_compatibility_or_upgrade_core",
            EIGEN_OS_VERSION, eigen_os_compatibility
        ));
    }
    Ok(())
}

fn compatibility_tuples_from_manifest() -> Vec<(String, String, String)> {
    if !COMPATIBILITY_MANIFEST_JSON.contains(&format!(
        "\"manifest_version\": \"{}\"",
        COMPATIBILITY_MANIFEST_VERSION
    )) {
        return Vec::new();
    }
    let mut tuples = Vec::new();
    for line in COMPATIBILITY_MANIFEST_JSON.lines() {
        let l = line.trim();
        if let Some(value) = l.strip_prefix("\"core_major\":") {
            let core = value.trim().trim_end_matches(',').to_string();
            tuples.push((core, String::new(), String::new()));
        } else if let Some(value) = l.strip_prefix("\"plugin_api_major\":") {
            if let Some(last) = tuples.last_mut() {
                last.1 = value.trim().trim_end_matches(',').to_string();
            }
        } else if let Some(value) = l.strip_prefix("\"eigen_lang_major\":") {
            if let Some(last) = tuples.last_mut() {
                last.2 = value.trim().trim_end_matches(',').to_string();
            }
        }
    }
    tuples
}

fn evaluate_plugin_trust(
    trust_profile: &str,
    signature_bundle_ref: &str,
    signer_identity: &str,
    rekor_log_index: &str,
    trust_root_ref: &str,
) -> Result<(), String> {
    if signature_bundle_ref.trim().is_empty() {
        return Err("PLUGIN_TRUST_UNSIGNED_REJECTED default_policy=sigstore_cosign".to_string());
    }
    match trust_profile {
        "keyless-public" => {
            if signer_identity.trim().is_empty() {
                return Err(
                    "PLUGIN_TRUST_FULCIO_IDENTITY_MISSING profile=keyless-public".to_string(),
                );
            }
            if rekor_log_index.trim().is_empty() {
                return Err("PLUGIN_TRUST_REKOR_PROOF_MISSING profile=keyless-public".to_string());
            }
            Ok(())
        }
        "private" | "airgap" => {
            if trust_root_ref.trim().is_empty() {
                return Err(format!(
                    "PLUGIN_TRUST_ROOT_MISSING profile={trust_profile} remediation=configure_self_hosted_sigstore_or_byo_pki"
                ));
            }
            Ok(())
        }
        other => Err(format!(
            "PLUGIN_TRUST_PROFILE_UNSUPPORTED profile={other} expected=keyless-public|private|airgap"
        )),
    }
}

fn activate_plugins(manifests: &[String]) -> Vec<PluginRecord> {
    let mut discovered = Vec::new();
    for manifest in manifests {
        let plugin_id =
            extract_toml_string(manifest, "plugin_id").unwrap_or_else(|| "unknown".to_string());
        let plugin_type = extract_toml_string(manifest, "plugin_type").unwrap_or_default();
        let plugin_api_version =
            extract_toml_string(manifest, "plugin_api_version").unwrap_or_default();
        let eigen_os_compatibility =
            extract_toml_string(manifest, "eigen_os_compatibility").unwrap_or_default();
        let eigen_lang_version =
            extract_toml_string(manifest, "eigen_lang_version").unwrap_or_default();
        let trust_profile = extract_toml_string(manifest, "trust_policy_profile")
            .unwrap_or_else(|| "keyless-public".to_string());
        let signature_bundle_ref =
            extract_toml_string(manifest, "signature_bundle_ref").unwrap_or_default();
        let signer_identity = extract_toml_string(manifest, "signer_identity").unwrap_or_default();
        let rekor_log_index = extract_toml_string(manifest, "rekor_log_index").unwrap_or_default();
        let trust_root_ref = extract_toml_string(manifest, "trust_root_ref").unwrap_or_default();
        let combined = format!(
            "{eigen_os_compatibility}|{eigen_lang_version}|{trust_profile}|{signature_bundle_ref}|{signer_identity}|{rekor_log_index}|{trust_root_ref}"
        );
        discovered.push(PluginRecord {
            plugin_id,
            plugin_type,
            plugin_api_version,
            eigen_os_compatibility: combined,
            lifecycle_state: PluginLifecycleState::Discovered,
            reason: None,
        });
    }

    discovered.sort_by(|a, b| (&a.plugin_type, &a.plugin_id).cmp(&(&b.plugin_type, &b.plugin_id)));
    let mut seen = BTreeSet::new();
    for r in &mut discovered {
        r.lifecycle_state = PluginLifecycleState::Registered;
        if !seen.insert((r.plugin_type.clone(), r.plugin_id.clone())) {
            r.lifecycle_state = PluginLifecycleState::Error;
            r.reason = Some("PLUGIN_CONFLICT_DUPLICATE_ID".to_string());
            continue;
        }
        let parts = r.eigen_os_compatibility.split('|').collect::<Vec<_>>();
        if parts.len() != 7 {
            r.lifecycle_state = PluginLifecycleState::Error;
            r.reason = Some("PLUGIN_COMPATIBILITY_MISSING".to_string());
            continue;
        }
        let (
            eigen_os_compatibility,
            eigen_lang_version,
            trust_profile,
            signature_bundle_ref,
            signer_identity,
            rekor_log_index,
            trust_root_ref,
        ) = (
            parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6],
        );
        if eigen_os_compatibility.is_empty() || eigen_lang_version.is_empty() {
            r.lifecycle_state = PluginLifecycleState::Error;
            r.reason = Some("PLUGIN_COMPATIBILITY_MISSING".to_string());
            continue;
        }
        if let Err(reason) = evaluate_compatibility(
            &r.plugin_api_version,
            eigen_os_compatibility,
            eigen_lang_version,
        ) {
            r.lifecycle_state = PluginLifecycleState::Error;
            r.reason = Some(reason);
            continue;
        }
        if let Err(reason) = evaluate_plugin_trust(
            trust_profile,
            signature_bundle_ref,
            signer_identity,
            rekor_log_index,
            trust_root_ref,
        ) {
            r.lifecycle_state = PluginLifecycleState::Error;
            r.reason = Some(reason);
            continue;
        }
        r.lifecycle_state = PluginLifecycleState::Validated;
        r.lifecycle_state = PluginLifecycleState::Active;
    }
    discovered
}

fn validate_plugin_manifest(manifest: &str) -> Result<(), String> {
    for field in [
        "manifest_schema_version",
        "plugin_id",
        "plugin_version",
        "plugin_type",
        "plugin_api_version",
        "eigen_os_compatibility",
        "eigen_lang_version",
        "signature_bundle_ref",
    ] {
        if extract_toml_string(manifest, field).is_none() {
            return Err(format!(
                "manifest validation failed: missing required field '{field}'"
            ));
        }
    }
    let plugin_type = extract_toml_string(manifest, "plugin_type").unwrap_or_default();
    validate_plugin_type(&plugin_type)?;
    if plugin_type == "policy" {
        validate_policy_plugin_manifest(manifest)?;
    }
    Ok(())
}

fn validate_plugin_type(plugin_type: &str) -> Result<(), String> {
    match plugin_type {
        "driver" | "compiler_backend" | "optimizer" | "policy" => Ok(()),
        other => Err(format!(
            "manifest validation failed: unsupported plugin_type '{other}', allowed: driver, compiler_backend, optimizer, policy"
        )),
    }
}

fn validate_policy_plugin_manifest(manifest: &str) -> Result<(), String> {
    let reason_codes = extract_toml_array(manifest, "reason_codes").ok_or_else(|| {
        "manifest validation failed: missing required [policy].reason_codes".to_string()
    })?;
    if reason_codes.is_empty() {
        return Err("manifest validation failed: [policy].reason_codes must be non-empty".to_string());
    }
    for code in reason_codes {
        if !code.starts_with("POLICY_")
            || !code
                .chars()
                .all(|c| c.is_ascii_uppercase() || c.is_ascii_digit() || c == '_')
        {
            return Err(format!(
                "manifest validation failed: invalid policy reason code '{code}'"
            ));
        }
    }
    let timeout_ms = extract_toml_u64(manifest, "timeout_ms").ok_or_else(|| {
        "manifest validation failed: missing required [policy].timeout_ms".to_string()
    })?;
    if !(10..=5000).contains(&timeout_ms) {
        return Err(
            "manifest validation failed: [policy].timeout_ms must be within 10..=5000".to_string(),
        );
    }
    let fallback_mode = extract_toml_string(manifest, "fallback_mode").ok_or_else(|| {
        "manifest validation failed: missing required [policy].fallback_mode".to_string()
    })?;
    match fallback_mode.as_str() {
        "deterministic_kernel" | "deterministic_core" => Ok(()),
        other => Err(format!(
            "manifest validation failed: unsupported [policy].fallback_mode '{other}', allowed: deterministic_kernel, deterministic_core"
        )),
    }
}

fn extract_toml_string(doc: &str, key: &str) -> Option<String> {
    let marker = format!("{key} = \"");
    let start = doc.find(&marker)? + marker.len();
    let end = doc[start..].find('\"')? + start;
    Some(doc[start..end].to_string())
}

fn extract_toml_array(doc: &str, key: &str) -> Option<Vec<String>> {
    let marker = format!("{key} = [");
    let start = doc.find(&marker)? + marker.len();
    let end = doc[start..].find(']')? + start;
    let body = &doc[start..end];
    Some(
        body.split(',')
            .map(str::trim)
            .filter(|item| !item.is_empty())
            .map(|item| item.trim_matches('"').to_string())
            .collect(),
    )
}

fn extract_toml_u64(doc: &str, key: &str) -> Option<u64> {
    let marker = format!("{key} = ");
    let start = doc.find(&marker)? + marker.len();
    let end = doc[start..]
        .find('\n')
        .map(|idx| start + idx)
        .unwrap_or(doc.len());
    doc[start..end].trim().parse().ok()
}

fn run_benchmark(args: &[String]) -> Result<(), String> {
    let Some(subcommand) = args.first() else {
        return Err("usage: eigen benchmark <run|compare> [args...]".to_string());
    };
    match subcommand.as_str() {
        "run" => run_benchmark_run(&args[1..]),
        "compare" => run_benchmark_compare(&args[1..]),
        other => Err(format!(
            "unknown benchmark subcommand: {other}. expected run|compare"
        )),
    }
}

fn run_benchmark_run(args: &[String]) -> Result<(), String> {
    let mut config_path: Option<PathBuf> = None;
    let mut output_mode = "human".to_string();
    let mut output_file: Option<PathBuf> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--config" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected value after --config".to_string());
                };
                config_path = Some(PathBuf::from(next));
                i += 2;
            }
            "--output" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected value after --output".to_string());
                };
                output_mode = next.clone();
                i += 2;
            }
            "--output-file" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected value after --output-file".to_string());
                };
                output_file = Some(PathBuf::from(next));
                i += 2;
            }
            unknown => return Err(format!("unknown benchmark run argument: {unknown}")),
        }
    }

    let Some(config_path) = config_path else {
        return Err(
            "usage: eigen benchmark run --config benchmark-run.json [--output json|human] [--output-file path]"
                .to_string(),
        );
    };
    let snapshot = parse_benchmark_run_config(&config_path)?;
    let json = benchmark_run_snapshot_json(&snapshot);
    if let Some(path) = output_file {
        std::fs::write(&path, format!("{json}\n"))
            .map_err(|e| format!("failed to write {}: {e}", path.display()))?;
    }
    render_benchmark_run_output(&snapshot, &json, &output_mode)
}

fn run_benchmark_compare(args: &[String]) -> Result<(), String> {
    let mut baseline_path: Option<PathBuf> = None;
    let mut candidate_path: Option<PathBuf> = None;
    let mut output_mode = "human".to_string();
    let mut output_file: Option<PathBuf> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--baseline" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected value after --baseline".to_string());
                };
                baseline_path = Some(PathBuf::from(next));
                i += 2;
            }
            "--candidate" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected value after --candidate".to_string());
                };
                candidate_path = Some(PathBuf::from(next));
                i += 2;
            }
            "--output" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected value after --output".to_string());
                };
                output_mode = next.clone();
                i += 2;
            }
            "--output-file" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected value after --output-file".to_string());
                };
                output_file = Some(PathBuf::from(next));
                i += 2;
            }
            unknown => return Err(format!("unknown benchmark compare argument: {unknown}")),
        }
    }
    let Some(baseline_path) = baseline_path else {
        return Err(
            "usage: eigen benchmark compare --baseline baseline.json --candidate candidate.json [--output json|human] [--output-file path]"
                .to_string(),
        );
    };
    let Some(candidate_path) = candidate_path else {
        return Err(
            "usage: eigen benchmark compare --baseline baseline.json --candidate candidate.json [--output json|human] [--output-file path]"
                .to_string(),
        );
    };
    let baseline = parse_benchmark_snapshot_file(&baseline_path)?;
    let candidate = parse_benchmark_snapshot_file(&candidate_path)?;
    let comparisons = compare_snapshots(&baseline, &candidate);
    let json = benchmark_comparison_json(&baseline, &candidate, &comparisons);
    if let Some(path) = output_file {
        std::fs::write(&path, format!("{json}\n"))
            .map_err(|e| format!("failed to write {}: {e}", path.display()))?;
    }
    render_benchmark_compare_output(&baseline, &candidate, &comparisons, &json, &output_mode)
}

fn parse_job_id_arg(args: &[String], usage: &str) -> Result<String, i32> {
    if args.len() != 1 {
        eprintln!("usage: {usage}");
        return Err(EXIT_USER_ERROR);
    }
    Ok(args[0].clone())
}

fn run_status(args: &[String]) -> Result<(), i32> {
    let job_id = parse_job_id_arg(args, "eigen status <job_id>")?;
    match jobspec::get_job_status_from_system_api(&job_id) {
        Ok(status) => {
            println!("job_id: {}", status.job_id);
            println!("state: {}", format_state_label(status.state));
            println!("stage: {}", status.stage);
            println!("progress: {:.1}%", f64::from(status.progress) * 100.0);
            println!("message: {}", status.message);
            match terminal_exit_code(status.state) {
                Some(0) | None => Ok(()),
                Some(code) => Err(code),
            }
        }
        Err(err) => Err(print_grpc_like_error("status", &err)),
    }
}

fn run_watch(args: &[String]) -> Result<(), i32> {
    let job_id = parse_job_id_arg(args, "eigen watch <job_id>")?;
    let updates = jobspec::stream_job_updates_from_system_api(&job_id)
        .map_err(|err| print_grpc_like_error("watch", &err))?;

    let mut last_state: Option<&str> = None;
    for update in updates {
        if should_render_live() {
            std::thread::sleep(Duration::from_millis(350));
        }
        let transition = last_state
            .map(|prev| format!("{prev} -> {}", update.state))
            .unwrap_or_else(|| format!("INIT -> {}", update.state));
        println!(
            "seq={} transition={} state={} stage={} progress={:.1}% message={}",
            update.event_seq,
            transition,
            format_state_label(update.state),
            update.stage,
            f64::from(update.progress) * 100.0,
            update.message
        );
        last_state = Some(update.state);
    }

    match last_state.and_then(terminal_exit_code) {
        Some(0) | None => Ok(()),
        Some(code) => Err(code),
    }
}

fn run_results(args: &[String]) -> Result<(), i32> {
    let job_id = parse_job_id_arg(args, "eigen results <job_id>")?;
    match jobspec::get_job_results_from_system_api(&job_id) {
        Ok(results) => {
            println!("job_id: {}", results.job_id);
            println!("state: {}", format_state_label(results.state));
            println!("counts:");
            for (k, v) in &results.counts {
                println!("  {k}: {v}");
            }
            println!("metadata:");
            for (k, v) in &results.metadata {
                println!("  {k}: {v}");
            }
            println!("artifacts:");
            let downloads = jobspec::download_and_verify_parquet_artifacts_from_qfs(
                &results.job_id,
                &results.artifacts,
            )
            .map_err(|err| print_grpc_like_error("results", &err))?;
            for artifact in downloads {
                println!(
                    "  {}: {} -> {} ({} bytes, parquet verified)",
                    artifact.kind,
                    artifact.qfs_uri,
                    artifact.local_path.display(),
                    artifact.bytes
                );
            }

            if results.state != "DONE" {
                eprintln!("error_code: {}", results.error_code.unwrap_or_default());
                eprintln!(
                    "error_summary: {}",
                    results.error_summary.unwrap_or_default()
                );
                return Err(EXIT_SERVER_ERROR);
            }
            Ok(())
        }
        Err(err) => Err(print_grpc_like_error("results", &err)),
    }
}

fn run_explain(args: &[String]) -> Result<(), i32> {
    let job_id = parse_job_id_arg(args, "eigen explain <job_id>")?;
    match jobspec::get_dispatch_rationale_from_system_api(&job_id) {
        Ok(rationale) => {
            println!("job_id: {job_id}");
            println!("version: {}", rationale.version);
            println!("policy_version: {}", rationale.policy_version);
            println!("selected_backend: {}", rationale.selected_backend);
            println!("selected_queue: {}", rationale.selected_queue);
            println!("reason_codes:");
            for code in &rationale.reason_codes {
                println!("  - {code}");
            }
            println!("timeline_ref: {}", rationale.timeline_ref);
            println!("logs_ref: {}", rationale.logs_ref);
            println!("trace_id: {}", rationale.trace_id.unwrap_or_default());
            println!("trace_ref: {}", rationale.trace_ref.unwrap_or_default());
            Ok(())
        }
        Err(err) => Err(print_grpc_like_error("explain", &err)),
    }
}

fn should_render_live() -> bool {
    use std::io::IsTerminal;
    std::io::stdout().is_terminal()
}

fn format_state_label(state: &str) -> String {
    let (icon, color) = match state {
        "DONE" => ("✓", "\x1b[32m"),
        "ERROR" | "CANCELLED" | "TIMEOUT" => ("✗", "\x1b[31m"),
        "RUNNING" | "COMPILING" => ("…", "\x1b[33m"),
        _ => ("·", "\x1b[36m"),
    };
    if should_render_live() {
        format!("{color}{icon} {state}\x1b[0m")
    } else {
        format!("{icon} {state}")
    }
}

fn terminal_exit_code(state: &str) -> Option<i32> {
    match state {
        "DONE" => Some(0),
        "ERROR" | "CANCELLED" | "TIMEOUT" => Some(EXIT_SERVER_ERROR),
        _ => None,
    }
}

fn print_grpc_like_error(cmd: &str, err: &jobspec::GrpcLikeError) -> i32 {
    eprintln!(
        "{cmd} failed: grpc code={} message={}",
        err.code.as_str(),
        err.message
    );
    if let Some(hint) = &err.retry_hint {
        eprintln!("retry_hint: {hint}");
    }

    match err.code {
        jobspec::GrpcCode::Unavailable | jobspec::GrpcCode::DeadlineExceeded => EXIT_NETWORK_ERROR,
        jobspec::GrpcCode::InvalidArgument
        | jobspec::GrpcCode::NotFound
        | jobspec::GrpcCode::FailedPrecondition => EXIT_USER_ERROR,
        jobspec::GrpcCode::Internal => EXIT_SERVER_ERROR,
    }
}

fn run_submit(args: &[String]) -> Result<(), String> {
    let mut job_file: Option<PathBuf> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "-f" | "--file" | "--job" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected path after -f/--file/--job".to_string());
                };
                job_file = Some(PathBuf::from(next));
                i += 2;
            }
            unknown => return Err(format!("unknown submit argument: {unknown}")),
        }
    }

    let Some(job_file) = job_file else {
        return Err("usage: eigen submit -f job.yaml".to_string());
    };

    let req = jobspec::build_submit_request_from_job_file(&job_file).map_err(|e| e.to_string())?;
    let response = jobspec::submit_job_to_system_api(&req);

    println!("job_id: {}", response.job_id);
    println!("hint: run `eigen status {}` to view state", response.job_id);
    println!(
        "hint: run `eigen watch {}` to stream updates",
        response.job_id
    );
    println!(
        "hint: run `eigen results {}` when the job is DONE",
        response.job_id
    );
    Ok(())
}

fn run_compile(args: &[String]) -> Result<(), String> {
    let mut job_file: Option<PathBuf> = None;
    let mut out_file: PathBuf = PathBuf::from("circuit.aqo.json");
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "-f" | "--file" | "--job" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected path after -f/--file/--job".to_string());
                };
                job_file = Some(PathBuf::from(next));
                i += 2;
            }
            "-o" | "--out" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected path after -o/--out".to_string());
                };
                out_file = PathBuf::from(next);
                i += 2;
            }
            unknown => return Err(format!("unknown compile argument: {unknown}")),
        }
    }
    let Some(job_path) = job_file else {
        return Err("usage: eigen compile -f job.yaml --out circuit.aqo.json".to_string());
    };
    let aqo_json = jobspec::compile_job_to_aqo_json(&job_path).map_err(|e| e.to_string())?;
    std::fs::write(&out_file, aqo_json)
        .map_err(|e| format!("failed to write {}: {e}", out_file.display()))?;
    println!("compiled_aqo: {}", out_file.display());
    Ok(())
}

fn run_visualize(args: &[String]) -> Result<(), String> {
    let mut aqo_file: Option<PathBuf> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "-f" | "--file" | "--aqo" => {
                let Some(next) = args.get(i + 1) else {
                    return Err("expected path after -f/--file/--aqo".to_string());
                };
                aqo_file = Some(PathBuf::from(next));
                i += 2;
            }
            unknown => return Err(format!("unknown visualize argument: {unknown}")),
        }
    }
    let Some(aqo_path) = aqo_file else {
        return Err("usage: eigen visualize -f circuit.aqo.json".to_string());
    };
    let aqo_json = std::fs::read_to_string(&aqo_path)
        .map_err(|e| format!("failed to read {}: {e}", aqo_path.display()))?;
    println!("{}", jobspec::visualize_aqo_json(&aqo_json));
    Ok(())
}

fn parse_benchmark_run_config(path: &PathBuf) -> Result<BenchmarkRunSnapshot, String> {
    let raw = std::fs::read_to_string(path)
        .map_err(|e| format!("failed to read benchmark config {}: {e}", path.display()))?;
    let workload = extract_required_json_string(&raw, "workload")?;
    let dataset = extract_required_json_string(&raw, "dataset")?;
    let backend = extract_required_json_string(&raw, "backend")?;
    let seed = extract_required_json_u64(&raw, "seed")?;
    let metrics = extract_required_metrics(&raw)?;
    let run_id = format!("run-{:016x}", fnv1a64(raw.as_bytes()));
    let created_at = format_seed_timestamp(seed);
    Ok(BenchmarkRunSnapshot {
        contract_version: BENCHMARK_RUN_CONTRACT_VERSION.to_string(),
        snapshot_version: BENCHMARK_RUN_SNAPSHOT_VERSION.to_string(),
        run_id,
        created_at,
        workload,
        dataset,
        backend,
        seed,
        metrics,
    })
}

fn parse_benchmark_snapshot_file(path: &PathBuf) -> Result<BenchmarkRunSnapshot, String> {
    let raw = std::fs::read_to_string(path)
        .map_err(|e| format!("failed to read benchmark snapshot {}: {e}", path.display()))?;
    Ok(BenchmarkRunSnapshot {
        contract_version: extract_required_json_string(&raw, "contract_version")?,
        snapshot_version: extract_required_json_string(&raw, "snapshot_version")?,
        run_id: extract_required_json_string(&raw, "run_id")?,
        created_at: extract_required_json_string(&raw, "created_at")?,
        workload: extract_required_json_string(&raw, "workload")?,
        dataset: extract_required_json_string(&raw, "dataset")?,
        backend: extract_required_json_string(&raw, "backend")?,
        seed: extract_required_json_u64(&raw, "seed")?,
        metrics: extract_required_metrics(&raw)?,
    })
}

fn render_benchmark_run_output(
    snapshot: &BenchmarkRunSnapshot,
    json: &str,
    output_mode: &str,
) -> Result<(), String> {
    match output_mode {
        "json" => {
            println!("{json}");
            Ok(())
        }
        "human" => {
            println!("benchmark run");
            println!("run_id: {}", snapshot.run_id);
            println!("contract_version: {}", snapshot.contract_version);
            println!("snapshot_version: {}", snapshot.snapshot_version);
            println!("created_at: {}", snapshot.created_at);
            println!("workload: {}", snapshot.workload);
            println!("dataset: {}", snapshot.dataset);
            println!("backend: {}", snapshot.backend);
            println!("seed: {}", snapshot.seed);
            println!("metrics:");
            for (name, value) in &snapshot.metrics {
                println!("  {name}: {}", format_float(*value));
            }
            Ok(())
        }
        other => Err(format!("unknown output mode: {other}. expected json|human")),
    }
}

fn render_benchmark_compare_output(
    baseline: &BenchmarkRunSnapshot,
    candidate: &BenchmarkRunSnapshot,
    comparisons: &[BenchmarkMetricComparison],
    json: &str,
    output_mode: &str,
) -> Result<(), String> {
    match output_mode {
        "json" => {
            println!("{json}");
            Ok(())
        }
        "human" => {
            println!("benchmark compare");
            println!("contract_version: {BENCHMARK_COMPARISON_CONTRACT_VERSION}");
            println!("comparison_version: {BENCHMARK_COMPARISON_VERSION}");
            println!("baseline_run_id: {}", baseline.run_id);
            println!("candidate_run_id: {}", candidate.run_id);
            println!("baseline_created_at: {}", baseline.created_at);
            println!("candidate_created_at: {}", candidate.created_at);
            println!("metrics:");
            for cmp in comparisons {
                println!(
                    "  {} [{}] baseline={} candidate={} delta={} delta_percent={} regression={}",
                    cmp.metric,
                    cmp.direction,
                    format_float(cmp.baseline),
                    format_float(cmp.candidate),
                    format_float(cmp.delta),
                    format_float(cmp.delta_percent),
                    cmp.regression
                );
            }
            Ok(())
        }
        other => Err(format!("unknown output mode: {other}. expected json|human")),
    }
}

fn compare_snapshots(
    baseline: &BenchmarkRunSnapshot,
    candidate: &BenchmarkRunSnapshot,
) -> Vec<BenchmarkMetricComparison> {
    let mut metrics: BTreeMap<String, (f64, f64)> = BTreeMap::new();
    for (name, value) in &baseline.metrics {
        metrics.insert(name.clone(), (*value, *value));
    }
    for (name, value) in &candidate.metrics {
        if let Some((baseline_value, candidate_value)) = metrics.get_mut(name) {
            *candidate_value = *value;
            *baseline_value = *baseline.metrics.get(name).unwrap_or(value);
        } else {
            metrics.insert(name.clone(), (*value, *value));
        }
    }
    metrics
        .into_iter()
        .map(|(metric, (baseline_value, candidate_value))| {
            let direction = metric_direction(&metric);
            let delta = candidate_value - baseline_value;
            let delta_percent = if baseline_value == 0.0 {
                0.0
            } else {
                (delta / baseline_value) * 100.0
            };
            let regression = match direction {
                "lower_is_better" => candidate_value > baseline_value,
                _ => candidate_value < baseline_value,
            };
            BenchmarkMetricComparison {
                metric,
                direction: direction.to_string(),
                baseline: baseline_value,
                candidate: candidate_value,
                delta,
                delta_percent,
                regression,
            }
        })
        .collect()
}

fn metric_direction(metric: &str) -> &'static str {
    if metric.contains("latency")
        || metric.contains("duration")
        || metric.contains("time")
        || metric.contains("error")
    {
        "lower_is_better"
    } else {
        "higher_is_better"
    }
}

fn benchmark_run_snapshot_json(snapshot: &BenchmarkRunSnapshot) -> String {
    let metrics = format_json_metrics(&snapshot.metrics);
    format!(
        "{{\"contract_version\":\"{}\",\"snapshot_version\":\"{}\",\"run_id\":\"{}\",\"created_at\":\"{}\",\"workload\":\"{}\",\"dataset\":\"{}\",\"backend\":\"{}\",\"seed\":{},\"metrics\":{{{metrics}}}}}",
        snapshot.contract_version,
        snapshot.snapshot_version,
        snapshot.run_id,
        snapshot.created_at,
        json_escape(&snapshot.workload),
        json_escape(&snapshot.dataset),
        json_escape(&snapshot.backend),
        snapshot.seed,
    )
}

fn benchmark_comparison_json(
    baseline: &BenchmarkRunSnapshot,
    candidate: &BenchmarkRunSnapshot,
    comparisons: &[BenchmarkMetricComparison],
) -> String {
    let comparison_rows: Vec<String> = comparisons
        .iter()
        .map(|cmp| {
            format!(
                "{{\"metric\":\"{}\",\"direction\":\"{}\",\"baseline\":{},\"candidate\":{},\"delta\":{},\"delta_percent\":{},\"regression\":{}}}",
                json_escape(&cmp.metric),
                cmp.direction,
                format_float(cmp.baseline),
                format_float(cmp.candidate),
                format_float(cmp.delta),
                format_float(cmp.delta_percent),
                cmp.regression,
            )
        })
        .collect();
    format!(
        "{{\"contract_version\":\"{BENCHMARK_COMPARISON_CONTRACT_VERSION}\",\"comparison_version\":\"{BENCHMARK_COMPARISON_VERSION}\",\"baseline_run_id\":\"{}\",\"candidate_run_id\":\"{}\",\"baseline_created_at\":\"{}\",\"candidate_created_at\":\"{}\",\"metrics\":[{}]}}",
        json_escape(&baseline.run_id),
        json_escape(&candidate.run_id),
        json_escape(&baseline.created_at),
        json_escape(&candidate.created_at),
        comparison_rows.join(","),
    )
}

fn format_json_metrics(metrics: &BTreeMap<String, f64>) -> String {
    metrics
        .iter()
        .map(|(k, v)| format!("\"{}\":{}", json_escape(k), format_float(*v)))
        .collect::<Vec<String>>()
        .join(",")
}

fn extract_required_metrics(doc: &str) -> Result<BTreeMap<String, f64>, String> {
    let marker = "\"metrics\":{";
    let start = doc
        .find(marker)
        .ok_or_else(|| "missing required field: metrics".to_string())?
        + marker.len();
    let end = doc[start..]
        .find('}')
        .ok_or_else(|| "invalid metrics object".to_string())?
        + start;
    let body = &doc[start..end];
    let mut metrics = BTreeMap::new();
    if body.trim().is_empty() {
        return Ok(metrics);
    }
    for entry in body.split(',') {
        let mut parts = entry.splitn(2, ':');
        let Some(raw_key) = parts.next() else {
            continue;
        };
        let Some(raw_val) = parts.next() else {
            continue;
        };
        let key = raw_key.trim().trim_matches('"').to_string();
        let value = raw_val
            .trim()
            .parse::<f64>()
            .map_err(|_| format!("metric '{key}' must be numeric"))?;
        metrics.insert(key, value);
    }
    Ok(metrics)
}

fn extract_required_json_string(doc: &str, field: &str) -> Result<String, String> {
    let marker = format!("\"{field}\":\"");
    let start = doc
        .find(&marker)
        .ok_or_else(|| format!("missing required field: {field}"))?
        + marker.len();
    let end = doc[start..]
        .find('"')
        .ok_or_else(|| format!("invalid string field: {field}"))?
        + start;
    Ok(doc[start..end].to_string())
}

fn extract_required_json_u64(doc: &str, field: &str) -> Result<u64, String> {
    let marker = format!("\"{field}\":");
    let start = doc
        .find(&marker)
        .ok_or_else(|| format!("missing required field: {field}"))?
        + marker.len();
    let end = doc[start..]
        .find(|ch: char| !ch.is_ascii_digit())
        .unwrap_or(doc.len() - start)
        + start;
    doc[start..end]
        .trim()
        .parse::<u64>()
        .map_err(|_| format!("field '{field}' must be an unsigned integer"))
}

fn json_escape(value: &str) -> String {
    value
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
}

fn format_float(value: f64) -> String {
    let mut s = format!("{value:.6}");
    while s.contains('.') && s.ends_with('0') {
        s.pop();
    }
    if s.ends_with('.') {
        s.push('0');
    }
    s
}

fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf29ce484222325u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

fn format_seed_timestamp(seed: u64) -> String {
    let day = (seed % 28) + 1;
    let hour = (seed / 28) % 24;
    let minute = (seed / (28 * 24)) % 60;
    let second = (seed / (28 * 24 * 60)) % 60;
    format!("2026-01-{day:02}T{hour:02}:{minute:02}:{second:02}Z")
}

fn print_help() {
    println!(
        "Eigen CLI\n\nUsage:\n  eigen <command> [args...]\n\nCommands:\n  help        Show this message\n  version     Print version\n  submit      Submit job: eigen submit -f job.yaml\n  status      Get job status: eigen status <job_id>\n  watch       Stream progress: eigen watch <job_id>\n  results     Fetch results: eigen results <job_id>\n  explain     Dispatch rationale: eigen explain <job_id>\n  compile     Compile locally: eigen compile -f job.yaml --out circuit.aqo.json\n  visualize   Visualize AQO: eigen visualize -f circuit.aqo.json\n  benchmark   Run/compare benchmark snapshots
  plugin      Scaffold/validate/package/activate plugin artifacts\n\nBenchmark examples (reproducible):\n  eigen benchmark run --config bench.json --output json --output-file baseline.json\n  eigen benchmark run --config bench-candidate.json --output json --output-file candidate.json\n  eigen benchmark compare --baseline baseline.json --candidate candidate.json --output human\n"
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    #[test]
    fn terminal_exit_code_matches_runtime_semantics() {
        assert_eq!(terminal_exit_code("DONE"), Some(0));
        assert_eq!(terminal_exit_code("ERROR"), Some(EXIT_SERVER_ERROR));
        assert_eq!(terminal_exit_code("CANCELLED"), Some(EXIT_SERVER_ERROR));
        assert_eq!(terminal_exit_code("TIMEOUT"), Some(EXIT_SERVER_ERROR));
        assert_eq!(terminal_exit_code("RUNNING"), None);
    }

    #[test]
    fn benchmark_run_snapshot_contract_fixture_is_stable() {
        let fixture_dir = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("fixtures")
            .join("benchmark");
        let config = fixture_dir.join("benchmark-run-config.json");
        let expected = std::fs::read_to_string(fixture_dir.join("expected-run-snapshot.json"))
            .expect("expected fixture");
        let snapshot = parse_benchmark_run_config(&config).expect("parse config");
        let json = benchmark_run_snapshot_json(&snapshot);
        assert_eq!(json, expected.trim());
        assert_eq!(snapshot.contract_version, BENCHMARK_RUN_CONTRACT_VERSION);
        assert_eq!(snapshot.snapshot_version, BENCHMARK_RUN_SNAPSHOT_VERSION);
    }

    #[test]
    fn benchmark_compare_contract_fixture_is_stable() {
        let fixture_dir = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("fixtures")
            .join("benchmark");
        let baseline = parse_benchmark_snapshot_file(&fixture_dir.join("baseline-snapshot.json"))
            .expect("parse baseline");
        let candidate = parse_benchmark_snapshot_file(&fixture_dir.join("candidate-snapshot.json"))
            .expect("parse candidate");
        let comparisons = compare_snapshots(&baseline, &candidate);
        let json = benchmark_comparison_json(&baseline, &candidate, &comparisons);
        let expected = std::fs::read_to_string(fixture_dir.join("expected-comparison.json"))
            .expect("expected fixture");
        assert_eq!(json, expected.trim());
        assert!(
            comparisons.iter().any(|metric| metric.regression),
            "at least one regression marker should be visible in fixture",
        );
    }

    #[test]
    fn plugin_ga_types_contract_fixtures_are_accepted() {
        let fixture_dir = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("fixtures")
            .join("plugins");

        for file in [
            "driver.toml",
            "compiler_backend.toml",
            "optimizer.toml",
            "policy.toml",
        ] {
            let manifest =
                std::fs::read_to_string(fixture_dir.join(file)).expect("fixture manifest");
            validate_plugin_manifest(&manifest).expect("ga type should validate");
        }
    }

    #[test]
    fn plugin_scheduler_type_is_rejected_for_phase6() {
        let fixture_dir = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("fixtures")
            .join("plugins");
        let manifest =
            std::fs::read_to_string(fixture_dir.join("scheduler.toml")).expect("fixture manifest");
        let err = validate_plugin_manifest(&manifest).expect_err("scheduler type must be rejected");
        assert!(err.contains("unsupported plugin_type 'scheduler'"));
        assert!(err.contains("driver, compiler_backend, optimizer, policy"));
    }

    #[test]
    fn plugin_manifest_rejects_non_ga_type() {
        let manifest = "manifest_schema_version = \"2.1.0\"\nplugin_id = \"io.eigen.x\"\nplugin_version = \"0.1.0\"\nplugin_type = \"analyzer\"\nplugin_api_version = \"2.1.0\"\neigen_os_compatibility = \">=0.6.0,<1.0.0\"\neigen_lang_version = \"0.1.0\"\nsignature_bundle_ref = \"oci://sig\"\n";
        let err = validate_plugin_manifest(manifest).expect_err("should fail");
        assert!(err.contains("unsupported plugin_type 'analyzer'"));
    }

     #[test]
    fn policy_manifest_requires_policy_contract_fields() {
        let manifest = "manifest_schema_version = \"2.1.0\"\nplugin_id = \"io.eigen.x\"\nplugin_version = \"0.1.0\"\nplugin_type = \"policy\"\nplugin_api_version = \"2.1.0\"\neigen_os_compatibility = \">=0.6.0,<1.0.0\"\neigen_lang_version = \"0.1.0\"\nsignature_bundle_ref = \"oci://sig\"\n\n[policy]\ntimeout_ms = 9\nfallback_mode = \"best_effort\"\n";
        let err = validate_plugin_manifest(manifest).expect_err("should fail");
        assert!(err.contains("[policy].reason_codes"));
    }

    #[test]
    fn plugin_activation_order_is_deterministic() {
        let manifests = vec![
            r#"manifest_schema_version = "2.0.0"
plugin_id = "io.eigen.z"
plugin_version = "0.1.0"
plugin_type = "optimizer"
plugin_api_version = "2.0.0"
eigen_os_compatibility = ">=0.6.0,<1.0.0"
eigen_lang_version = "0.1.0"
signature_bundle_ref = "oci://sig"
signer_identity = "https://github.com/org/repo/.github/workflows/release.yml@refs/tags/v0.1.0"
rekor_log_index = "42"
"#
            .to_string(),
            r#"manifest_schema_version = "2.0.0"
plugin_id = "io.eigen.a"
plugin_version = "0.1.0"
plugin_type = "driver"
plugin_api_version = "2.0.0"
eigen_os_compatibility = ">=0.6.0,<1.0.0"
eigen_lang_version = "0.1.0"
signature_bundle_ref = "oci://sig"
signer_identity = "https://github.com/org/repo/.github/workflows/release.yml@refs/tags/v0.1.0"
rekor_log_index = "42"
"#
            .to_string(),
        ];
        let records = activate_plugins(&manifests);
        assert_eq!(records[0].plugin_id, "io.eigen.a");
        assert_eq!(records[0].lifecycle_state, PluginLifecycleState::Active);
        assert_eq!(records[1].plugin_id, "io.eigen.z");
    }

    #[test]
    fn plugin_conflicts_fail_closed_with_reason() {
        let manifests = vec![
            r#"manifest_schema_version = "2.0.0"
plugin_id = "io.eigen.same"
plugin_version = "0.1.0"
plugin_type = "driver"
plugin_api_version = "2.0.0"
eigen_os_compatibility = ">=0.6.0,<1.0.0"
eigen_lang_version = "0.1.0"
signature_bundle_ref = "oci://sig"
signer_identity = "https://github.com/org/repo/.github/workflows/release.yml@refs/tags/v0.1.0"
rekor_log_index = "42"
"#
            .to_string(),
            r#"manifest_schema_version = "2.0.0"
plugin_id = "io.eigen.same"
plugin_version = "0.1.0"
plugin_type = "driver"
plugin_api_version = "2.0.0"
eigen_os_compatibility = ">=0.6.0,<1.0.0"
eigen_lang_version = "0.1.0"
signature_bundle_ref = "oci://sig"
signer_identity = "https://github.com/org/repo/.github/workflows/release.yml@refs/tags/v0.1.0"
rekor_log_index = "42"
"#
            .to_string(),
        ];
        let records = activate_plugins(&manifests);
        assert_eq!(records[0].lifecycle_state, PluginLifecycleState::Active);
        assert_eq!(records[1].lifecycle_state, PluginLifecycleState::Error);
        assert!(
            records[1]
                .reason
                .as_deref()
                .unwrap_or_default()
                .contains("PLUGIN_CONFLICT_DUPLICATE_ID")
        );
    }

    #[test]
    fn plugin_unsupported_matrix_is_blocked_with_remediation() {
        let manifests = vec![
            r#"manifest_schema_version = "2.0.0"
plugin_id = "io.eigen.bad"
plugin_version = "0.1.0"
plugin_type = "driver"
plugin_api_version = "3.0.0"
eigen_os_compatibility = ">=0.6.0,<1.0.0"
eigen_lang_version = "0.1.0"
"#
            .to_string(),
        ];
        let records = activate_plugins(&manifests);
        assert_eq!(records[0].lifecycle_state, PluginLifecycleState::Error);
        assert!(
            records[0]
                .reason
                .as_deref()
                .unwrap_or_default()
                .contains("remediation=")
        );
    }

    #[test]
    fn compatibility_manifest_fixture_is_versioned() {
        assert!(COMPATIBILITY_MANIFEST_JSON.contains("\"manifest_version\": \"1.0.0\""));
        assert!(COMPATIBILITY_MANIFEST_JSON.contains("\"deprecation_days\": 90"));
        assert!(COMPATIBILITY_MANIFEST_JSON.contains("\"deprecation_minors\": 2"));
    }

    #[test]
    fn compatibility_rejection_has_stable_reason_and_hint() {
        let err = evaluate_compatibility("3.0.0", ">=0.6.0,<1.0.0", "0.1.0")
            .expect_err("unsupported combo");
        assert!(err.contains("PLUGIN_COMPATIBILITY_MATRIX_UNSUPPORTED"));
        assert!(err.contains("hint=runtime->cli->plugin_api->eigen_lang"));
    }
}
                       

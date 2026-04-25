//! Eigen CLI - MVP.

mod jobspec;

use std::path::PathBuf;
use std::time::Duration;

const EXIT_USER_ERROR: i32 = 2;
const EXIT_NETWORK_ERROR: i32 = 3;
const EXIT_SERVER_ERROR: i32 = 4;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() <= 1 {
        print_help();
        std::process::exit(EXIT_USER_ERROR);
    }

    match args[1].as_str() {
        "help" | "--help" | "-h" => print_help(),
        "version" | "--version" | "-V" => println!("eigen-cli 0.1.0"),
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

fn print_help() {
    println!(
        "Eigen CLI (scaffold)\n\nUsage:\n  eigen <command> [args...]\n\nCommands:\n  help        Show this message\n  version     Print version\n  submit      Submit job: eigen submit -f job.yaml\n  status      Get job status: eigen status <job_id>\n  watch       Stream progress: eigen watch <job_id>\n  results     Fetch results: eigen results <job_id>\n  compile     Compile locally: eigen compile -f job.yaml --out circuit.aqo.json\n  visualize   Visualize AQO: eigen visualize -f circuit.aqo.json\n"
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn terminal_exit_code_matches_runtime_semantics() {
        assert_eq!(terminal_exit_code("DONE"), Some(0));
        assert_eq!(terminal_exit_code("ERROR"), Some(EXIT_SERVER_ERROR));
        assert_eq!(terminal_exit_code("CANCELLED"), Some(EXIT_SERVER_ERROR));
        assert_eq!(terminal_exit_code("TIMEOUT"), Some(EXIT_SERVER_ERROR));
        assert_eq!(terminal_exit_code("RUNNING"), None);
    }
}

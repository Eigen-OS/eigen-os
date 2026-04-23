//! Eigen CLI - MVP scaffold.
//!
//! This binary will evolve into the primary user interface for Phase 0:
//! `submit`, `status`, `result`, `compile`, `visualize`.

mod jobspec;

use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() <= 1 {
        print_help();
        std::process::exit(2);
    }

    match args[1].as_str() {
        "help" | "--help" | "-h" => {
            print_help();
        }
        "version" | "--version" | "-V" => {
            println!("eigen-cli 0.1.0 (scaffold)");
        }
        "submit" => {
            if let Err(err) = run_submit(&args[2..]) {
                eprintln!("submit failed: {err}");
                std::process::exit(2);
            }
        }
        cmd => {
            println!("Command '{cmd}' is not implemented yet (scaffold). Use 'eigen help'.");
            std::process::exit(1);
        }
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
    println!(
        "hint: run `eigen status {}` to watch progress",
        response.job_id
    );
    println!(
        "hint: run `eigen result {}` when the job is DONE",
        response.job_id
    );
    Ok(())
}

fn print_help() {
    println!(
        "Eigen CLI (scaffold)\n\nUsage:\n  eigen <command> [args...]\n\nCommands:\n  help        Show this message\n  version     Print version\n  submit      Submit job: eigen submit -f job.yaml\n\nMVP commands (planned):\n  submit, status, result, compile, visualize\n"
    );
}

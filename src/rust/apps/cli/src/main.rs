//! Eigen CLI - MVP scaffold.
//!
//! This binary will evolve into the primary user interface for Phase 0:
//! `submit`, `status`, `result`, `compile`, `visualize`.

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
        cmd => {
            println!("Command '{cmd}' is not implemented yet (scaffold). Use 'eigen help'.");
            std::process::exit(1);
        }
    }
}

fn print_help() {
    println!(
        "Eigen CLI (scaffold)\n\nUsage:\n  eigen <command> [args...]\n\nCommands:\n  help        Show this message\n  version     Print version\n\nMVP commands (planned):\n  submit, status, result, compile, visualize\n"
    );
}

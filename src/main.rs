use jarviis_core::config::KernelConfig;
use jarviis_core::fsm::FsmKernel;
use jarviis_core::governance::GovernanceSubsystem;
use jarviis_core::identity::IdentitySubsystem;
use jarviis_core::inference;
use jarviis_core::memory::MemorySubsystem;
use jarviis_core::tools::ToolSubsystem;

use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() {
    // Initialise structured logging. Set RUST_LOG=debug for verbose FSM traces.
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("jarviis_core=info,warn")),
        )
        .init();

    let config = KernelConfig::default();

    // Initialise all subsystems (fail fast on startup errors).
    let memory = MemorySubsystem::new(&config).expect("failed to initialise memory subsystem");
    
    // Select inference backend: Ollama (preferred) → Llama (feature-gated) → Mock (fallback)
    let inference = inference::select_inference_engine(&config);
    
    let identity   = IdentitySubsystem::new(&config);
    let governance = GovernanceSubsystem::new(&config);
    let tools      = ToolSubsystem::new(&config);

    let kernel = FsmKernel::new(config, identity, governance, memory, inference, tools);

    println!("╔══════════════════════════════════════════╗");
    println!("║  JARVIIS Cognitive Kernel OS  v1.1       ║");
    println!("║  Deterministic Local Runtime — Ready     ║");
    println!("╚══════════════════════════════════════════╝");
    println!("JARVIIS online. Awaiting input, Sir.\n");
    println!("  (type 'exit' or 'quit' to shut down)\n");

    use tokio::io::{self, AsyncBufReadExt, BufReader};

    let stdin = BufReader::new(io::stdin());
    let mut lines = stdin.lines();

    loop {
        print!("> ");
        use std::io::Write;
        let _ = std::io::stdout().flush();

        match lines.next_line().await {
            Ok(Some(line)) => {
                let line = line.trim().to_string();
                if line.is_empty() {
                    continue;
                }
                if line.eq_ignore_ascii_case("exit") || line.eq_ignore_ascii_case("quit") {
                    println!("\nGoodbye, Sir.");
                    break;
                }
                let response = kernel.run_cycle(line).await;
                println!("\n{response}\n");
            }
            Ok(None) => {
                // EOF — stdin closed.
                println!("\nGoodbye, Sir.");
                break;
            }
            Err(e) => {
                eprintln!("stdin error: {e}");
                break;
            }
        }
    }
}

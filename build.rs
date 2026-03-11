use std::env;
use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::Duration;

fn main() {
    // Only run this mitigation on Windows.
    if env::var("CARGO_CFG_WINDOWS").is_ok() {
        let out_dir = env::var("OUT_DIR").unwrap_or_default();
        if out_dir.is_empty() {
            return;
        }

        // Navigate up from OUT_DIR to the target directory (e.g. target/debug/deps).
        // OUT_DIR is typically: target/debug/build/jarviis-core-[hash]/out
        let mut target_dir = PathBuf::from(out_dir);
        target_dir.pop(); // remove 'out'
        target_dir.pop(); // remove 'jarviis-core-[hash]'
        target_dir.pop(); // remove 'build'
        target_dir.push("deps");

        if target_dir.exists() {
            // Find any stale .rcgu.o files that tend to cause "os error 32"
            // due to being locked by previous crashed build steps or Defender.
            if let Ok(entries) = fs::read_dir(&target_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if let Some(ext) = path.extension() {
                        if ext == "o" || path.to_string_lossy().contains(".rcgu") {
                            // Try to delete with retries
                            let mut retries = 3;
                            while retries > 0 {
                                if fs::remove_file(&path).is_ok() {
                                    break;
                                }
                                retries -= 1;
                                thread::sleep(Duration::from_millis(100));
                            }
                            // If it still fails, we ignore it rather than failing the build script.
                            // The linker might still complain, but this mitigation improves success rates.
                        }
                    }
                }
            }
        }
    }
}

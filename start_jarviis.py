import sys
import time
import requests
import json
import os

# Adjust python path to include 'jarviis' so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
jarviis_dir = os.path.join(current_dir, "jarviis")
if jarviis_dir not in sys.path:
    sys.path.insert(0, jarviis_dir)

governance_dir = os.path.join(current_dir, "governance")
if governance_dir not in sys.path:
    sys.path.insert(0, governance_dir)

# Import JARVIIS components for main loop
try:
    from main_complete import main_complete as run_jarviis
except ImportError:
    # Fallback if main_complete is not yet in sys.path correctly or named differently
    # But based on user request, we assume it's available or we implement the logic here.
    # The user asked to "Import jarviis.main_complete logic".
    # Inspecting previous files, 'jarviis/main_complete.py' exists.
    from jarviis.main_complete import main_complete as run_jarviis

# Constants
OLLAMA_API = "http://localhost:11434"
MODEL_GOVERNANCE = "smollm2"
MODEL_REASONING = "hermes-mistral"

def check_ollama_running():
    """Verify Ollama is running."""
    print(" [BOOT] Checking Ollama status...")
    try:
        response = requests.get(f"{OLLAMA_API}/api/tags", timeout=2)
        if response.status_code == 200:
            print(" [PASS] Ollama is running.")
            return True
    except requests.exceptions.RequestException:
        print("\n [FAIL] Ollama is not running.")
        print("        Run: ollama serve")
        sys.exit(1)

def check_model_exists(model_name):
    """Verify required model exists."""
    print(f" [BOOT] Checking for model '{model_name}'...")
    try:
        response = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
        if response.status_code != 200:
             print(f" [FAIL] Failed to list models. HTTP {response.status_code}")
             sys.exit(1)
             
        data = response.json()
        models = [m['name'] for m in data.get('models', [])]
        
        # Check standard name and :latest tag
        if model_name in models or f"{model_name}:latest" in models:
            print(f" [PASS] Model '{model_name}' found.")
            return True
        else:
            print(f"\n [FAIL] Model '{model_name}' not found.")
            print(f"        Run: ollama pull {model_name}") # Or create if custom
            print(f"        (Note: Ensure '{model_name}' exists in 'ollama list')")
            sys.exit(1)
            
    except Exception as e:
        print(f" [ERROR] Failed to check models: {e}")
        sys.exit(1)

def warmup_model(model_name):
    """Wake up model to prevent first-token latency spike."""
    print(f" [BOOT] Warming up '{model_name}' (this may take 5-10s)...")
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
        "options": {"num_predict": 1}
    }
    
    try:
        response = requests.post(f"{OLLAMA_API}/api/chat", json=payload, timeout=30)
        if response.status_code == 200:
            print(f" [PASS] '{model_name}' is ready.")
        else:
            print(f" [WARN] Warmup failed for '{model_name}': HTTP {response.status_code}")
            
    except Exception as e:
        print(f" [WARN] Warmup failed for '{model_name}': {e}")

def main():
    """Main system entry point."""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                   JARVIIS STARTUP                        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    
    # 1. System Checks
    check_ollama_running()
    check_model_exists(MODEL_GOVERNANCE)
    check_model_exists(MODEL_REASONING)
    
    # 2. Initialization
    print(" [BOOT] Initializing JARVIIS core...")
    warmup_model(MODEL_GOVERNANCE)
    warmup_model(MODEL_REASONING)
    
    print("║                   SYSTEM READY                           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    # 3. Start Application
    # We import this inside main to avoid initializing checks before startup
    try:
        run_jarviis()
    except KeyboardInterrupt:
        print("\n[EXIT] Shutdown by user.")
    except Exception as e:
        print(f"\n[CRITICAL] System crash: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

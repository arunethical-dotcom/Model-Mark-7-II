import sys
from pathlib import Path
import inspect

output_file = Path("c:/Users/Arun/model/Cursor Int/jarviis/test_debug_log.txt")

with open(output_file, "w", encoding="utf-8") as f:
    def log(msg):
        print(msg)
        f.write(msg + "\n")
        f.flush()

    # Setup paths like in the real test
    jarviis_path = Path("c:/Users/Arun/model/Cursor Int/jarviis")
    project_root = Path("c:/Users/Arun/model/Cursor Int")
    governance_path = Path("c:/Users/Arun/model/Cursor Int/governance")

    sys.path.insert(0, str(governance_path))
    sys.path.insert(0, str(jarviis_path))
    sys.path.insert(0, str(project_root))

    log("DEBUG: Importing cognitive_core...")
    try:
        import cognitive_core
        log(f"DEBUG: File: {cognitive_core.__file__}")
        from cognitive_core import CognitiveOrchestrator
        sig = inspect.signature(CognitiveOrchestrator.__init__)
        log(f"DEBUG: Init signature: {sig}")
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc(file=f)

    log("DEBUG: Importing governed_llm_backend...")
    try:
        from reasoning.governed_llm_backend import GovernedLLMBackend
        log(f"DEBUG: GovernedLLMBackend imported")
        
        # Test instantiation
        try:
             # Just instantiate and catch error
             backend = GovernedLLMBackend(backend_type="mock")
             log("DEBUG: Instantiation successful")
        except Exception as e:
             log(f"ERROR in instantiation: {e}")
    except Exception as e:
        log(f"ERROR importing backend: {e}")


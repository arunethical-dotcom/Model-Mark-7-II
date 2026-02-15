import sys
import os

# Ensure we run from the project root so imports and DB paths work correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from memory.sqlite_store import SQLiteStore

store = SQLiteStore()

ids = [107,108,109,110,111,112,113,114]

for mid in ids:
    ok = store.soft_delete_memory(mid)
    print(f"memory {mid} -> deleted: {ok}")

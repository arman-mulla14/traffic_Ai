import sys
from pathlib import Path

# Automatically ensure 'backend' directory is at the head of Python module search path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


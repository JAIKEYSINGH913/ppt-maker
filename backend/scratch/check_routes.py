import sys
from pathlib import Path

# Add backend/src to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

try:
    from md2deck.api import app
    print("FastAPI Routes:")
    for route in app.routes:
        methods = getattr(route, "methods", ["GET"])
        print(f"{methods} {route.path}")
except Exception as e:
    print(f"Error loading app: {e}")
    import traceback
    traceback.print_exc()

import sys
import os
from pathlib import Path

AI_ROOT = Path(__file__).parent.parent
SRC_ROOT = AI_ROOT / "src"
REPO_ROOT = AI_ROOT.parent.parent

for p in [str(REPO_ROOT), str(AI_ROOT), str(SRC_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5433/iterateswarm")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("USE_APSCHEDULER", "true")
os.environ.setdefault("PYTHONPATH", f"{REPO_ROOT}:{AI_ROOT}:{SRC_ROOT}")
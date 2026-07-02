import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

sys.path.insert(0, str(project_root / "app" / "src"))
sys.path.insert(0, str(project_root / "core" / "src"))

from app import main

if __name__ == "__main__":
    main()

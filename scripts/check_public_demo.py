"""Run the bundled smoke checks without installing a test runner."""
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[1]
count = 0
for path in (root / "tests" / "test_demo.py", root / "tests" / "test_export.py"):
    namespace = runpy.run_path(str(path))
    for name in sorted(namespace):
        if name.startswith("test_") and callable(namespace[name]):
            namespace[name]()
            count += 1
            print(f"PASS {path.name}::{name}")
print(f"{count} checks passed; synthetic smoke/regression only")

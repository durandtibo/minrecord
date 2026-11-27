from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "generate_versions", ROOT / "dev" / "generate_versions.py"
)
assert SPEC is not None
assert SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_fetch_package_versions_of_the_project_dependencies() -> None:
    assert list(module.fetch_package_versions(ROOT)) == ["coola"]

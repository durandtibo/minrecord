from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

SCRIPT = Path(__file__).resolve().parents[3] / "dev" / "generate_versions.py"
SPEC = importlib.util.spec_from_file_location("generate_versions", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.fixture
def feu_mock() -> Generator[Mock]:
    r"""Patch the ``feu`` function used by
    ``fetch_package_versions``."""
    with patch.object(
        module, "fetch_feu_package_versions", return_value={"coola": ["2.0"]}
    ) as mock:
        yield mock


############################################
#     Tests for fetch_package_versions     #
############################################


@pytest.mark.usefixtures("feu_mock")
def test_fetch_package_versions_returns_versions(tmp_path: Path) -> None:
    assert module.fetch_package_versions(tmp_path) == {"coola": ["2.0"]}


def test_fetch_package_versions_reads_pyproject_of_base_dir(tmp_path: Path, feu_mock: Mock) -> None:
    module.fetch_package_versions(tmp_path)
    feu_mock.assert_called_once_with(tmp_path / "pyproject.toml", include_lower_bound=True)


def test_fetch_package_versions_error(tmp_path: Path, feu_mock: Mock) -> None:
    feu_mock.side_effect = FileNotFoundError("missing pyproject.toml")
    with pytest.raises(FileNotFoundError, match=r"missing pyproject\.toml"):
        module.fetch_package_versions(tmp_path)


##########################
#     Tests for main     #
##########################


def test_main_saves_versions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "dev" / "config" / "package_versions.json"
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(module, "__file__", str(tmp_path / "dev" / "generate_versions.py"))
    with patch.object(module, "fetch_package_versions", return_value={"coola": ["2.0"]}):
        module.main()
    assert json.loads(path.read_text()) == {"coola": ["2.0"]}


def test_main_overwrites_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "dev" / "config" / "package_versions.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"old": ["0.1"]}')
    monkeypatch.setattr(module, "__file__", str(tmp_path / "dev" / "generate_versions.py"))
    with patch.object(module, "fetch_package_versions", return_value={"coola": ["2.0"]}):
        module.main()
    assert json.loads(path.read_text()) == {"coola": ["2.0"]}

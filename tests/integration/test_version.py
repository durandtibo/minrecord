from __future__ import annotations

from importlib.metadata import version

import minrecord
from minrecord import _get_version


def test_version_is_the_installed_version() -> None:
    assert minrecord.__version__ == version("minrecord")


def test_get_version_is_the_installed_version() -> None:
    assert _get_version() == version("minrecord")

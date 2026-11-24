from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import minrecord
from minrecord import _get_version

##################################
#     Tests for _get_version     #
##################################


def test_get_version_installed() -> None:
    with patch("minrecord.version", return_value="1.2.3") as mock_version:
        assert _get_version() == "1.2.3"
    mock_version.assert_called_once_with("minrecord")


def test_get_version_not_installed() -> None:
    with patch("minrecord.version", side_effect=PackageNotFoundError("minrecord not found")):
        assert _get_version() == "0.0.0"


def test_version_is_a_str() -> None:
    assert isinstance(minrecord.__version__, str)

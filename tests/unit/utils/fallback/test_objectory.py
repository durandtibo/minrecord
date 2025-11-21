from __future__ import annotations

import pytest

from minrecord.utils.fallback.objectory import AbstractFactory


def test_abstract_factory() -> None:
    class Factory(metaclass=AbstractFactory): ...

    with pytest.raises(RuntimeError, match=r"'objectory' package is required but not installed."):
        Factory.factory()

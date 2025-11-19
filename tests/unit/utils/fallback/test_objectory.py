from __future__ import annotations

import pytest

from minrecord.utils.fallback.objectory import AbstractFactory, full_object_name


def test_abstract_factory() -> None:
    class Factory(metaclass=AbstractFactory): ...

    with pytest.raises(RuntimeError, match=r"'objectory' package is required but not installed."):
        Factory.factory()


def test_full_object_name() -> None:
    with pytest.raises(RuntimeError, match=r"'objectory' package is required but not installed."):
        full_object_name()

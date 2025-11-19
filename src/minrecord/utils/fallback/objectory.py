r"""Contain fallback implementations used when ``objectory`` dependency
is not available."""

from __future__ import annotations

__all__ = ["OBJECT_TARGET", "AbstractFactory", "full_object_name"]

from abc import ABCMeta
from typing import Any

from minrecord.utils.imports import raise_error_objectory_missing

OBJECT_TARGET = "_target_"


class AbstractFactory(ABCMeta):
    r"""Fallback of ``objectory.AbstractFactory``."""

    def factory(cls, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        r"""Fallback of ``objectory.AbstractFactory.factory``."""
        raise_error_objectory_missing()


def full_object_name(*args: Any, **kwargs: Any) -> str:  # noqa: ARG001
    r"""Fallback of ``objectory.utils.full_object_name``."""
    raise_error_objectory_missing()

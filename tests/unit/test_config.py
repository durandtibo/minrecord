from __future__ import annotations

import pytest

from minrecord.config import Config


def test_config_init_default_max_size() -> None:
    """Test that Config initializes with the default max_size."""
    assert Config().get_max_size() == Config.DEFAULT_MAX_SIZE


def test_config_init_default_max_size_value() -> None:
    """Test that the default max_size is 10."""
    assert Config().get_max_size() == 10


def test_config_get_max_size() -> None:
    """Test getting the max_size."""
    assert Config().get_max_size() == 10


def test_config_set_max_size_valid() -> None:
    """Test setting max_size to a valid positive integer."""
    config = Config()
    config.set_max_size(5)
    assert config.get_max_size() == 5


def test_config_set_max_size_one() -> None:
    """Test setting max_size to 1."""
    config = Config()
    config.set_max_size(1)
    assert config.get_max_size() == 1


def test_config_set_max_size_large_value() -> None:
    """Test setting max_size to a large value."""
    config = Config()
    config.set_max_size(1000)
    assert config.get_max_size() == 1000


def test_config_set_max_size_zero_raises_value_error() -> None:
    """Test that setting max_size to 0 raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        config.set_max_size(0)


def test_config_set_max_size_negative_raises_value_error() -> None:
    """Test that setting max_size to a negative integer raises
    ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got -1"):
        config.set_max_size(-1)


def test_config_set_max_size_float_raises_value_error() -> None:
    """Test that setting max_size to a float raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 5.5"):
        config.set_max_size(5.5)


def test_config_set_max_size_string_raises_value_error() -> None:
    """Test that setting max_size to a string raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 10"):
        config.set_max_size("10")


def test_config_set_max_size_none_raises_value_error() -> None:
    """Test that setting max_size to None raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got None"):
        config.set_max_size(None)


def test_config_reset_max_size() -> None:
    """Test resetting max_size to the default value."""
    config = Config()
    config.set_max_size(5)
    assert config.get_max_size() == 5
    config.reset_max_size()
    assert config.get_max_size() == Config.DEFAULT_MAX_SIZE


def test_config_reset_max_size_to_ten() -> None:
    """Test that reset_max_size resets to 10."""
    config = Config()
    config.set_max_size(20)
    config.reset_max_size()
    assert config.get_max_size() == 10


def test_config_reset_max_size_when_already_default() -> None:
    """Test resetting max_size when it's already at the default
    value."""
    config = Config()
    config.reset_max_size()
    assert config.get_max_size() == Config.DEFAULT_MAX_SIZE


def test_config_multiple_set_operations() -> None:
    """Test multiple set_max_size operations in sequence."""
    config = Config()
    config.set_max_size(5)
    assert config.get_max_size() == 5
    config.set_max_size(15)
    assert config.get_max_size() == 15
    config.set_max_size(3)
    assert config.get_max_size() == 3


def test_config_set_reset_set() -> None:
    """Test setting, resetting, then setting again."""
    config = Config()
    config.set_max_size(7)
    assert config.get_max_size() == 7
    config.reset_max_size()
    assert config.get_max_size() == 10
    config.set_max_size(12)
    assert config.get_max_size() == 12


def test_config_independence_between_instances() -> None:
    """Test that different Config instances are independent."""
    config1 = Config()
    config2 = Config()

    config1.set_max_size(5)
    assert config1.get_max_size() == 5
    assert config2.get_max_size() == 10

    config2.set_max_size(15)
    assert config1.get_max_size() == 5
    assert config2.get_max_size() == 15

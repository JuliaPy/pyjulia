"""
Unit tests which can be done without loading `libjulia`.
"""

import os

import pytest

from julia.core import raise_separate_cache_error

try:
    from types import SimpleNamespace
except ImportError:
    from argparse import Namespace as SimpleNamespace  # Python 2


def dummy_juliainfo():
    somepath = os.devnull  # some random path
    return SimpleNamespace(
        pyprogramname=somepath,
        libpython=somepath,
    )


def test_raise_separate_cache_error_statically_linked():
    runtime = "julia"
    jlinfo = dummy_juliainfo()
    with pytest.raises(RuntimeError) as excinfo:
        raise_separate_cache_error(
            runtime, jlinfo,
            _determine_if_statically_linked=lambda: True)
    assert "is statically linked" in str(excinfo.value)


def test_raise_separate_cache_error_dynamically_linked():
    runtime = "julia"
    jlinfo = dummy_juliainfo()
    with pytest.raises(RuntimeError) as excinfo:
        raise_separate_cache_error(
            runtime, jlinfo,
            _determine_if_statically_linked=lambda: False)
    assert "have to match exactly" in str(excinfo.value)

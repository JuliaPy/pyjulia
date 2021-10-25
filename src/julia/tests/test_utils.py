"""
Unit tests which can be done without loading `libjulia`.
"""

import os

import pytest

from julia.core import UnsupportedPythonError

from .test_compatible_exe import runcode
from .utils import _retry_on_failure, retry_failing_if_windows

try:
    from types import SimpleNamespace
except ImportError:
    from argparse import Namespace as SimpleNamespace  # Python 2


def dummy_juliainfo():
    somepath = os.devnull  # some random path
    return SimpleNamespace(julia="julia", python=somepath, libpython_path=somepath)


def test_unsupported_python_error_statically_linked():
    jlinfo = dummy_juliainfo()
    err = UnsupportedPythonError(jlinfo)
    err.statically_linked = True
    assert "is statically linked" in str(err)


def test_unsupported_python_error_dynamically_linked():
    jlinfo = dummy_juliainfo()
    err = UnsupportedPythonError(jlinfo)
    err.statically_linked = False
    assert "have to match exactly" in str(err)


def test_retry_on_failure():
    c = [0]

    def f():
        c[0] += 1
        assert c[0] >= 2

    _retry_on_failure(f)
    assert c[0] == 2


@pytest.mark.pyjulia__using_default_setup
@pytest.mark.julia
def test_atexit():
    check_atexit()


@retry_failing_if_windows
def check_atexit():
    proc = runcode(
        '''
        import os
        from julia import Julia
        jl = Julia(runtime=os.getenv("PYJULIA_TEST_RUNTIME"), debug=True)

        jl_atexit = jl.eval("""
        function(f)
            atexit(() -> f())
        end
        """)

        @jl_atexit
        def _():
            print("atexit called")
        '''
    )
    assert "atexit called" in proc.stdout

"""
Unit tests which can be done without loading `libjulia`.
"""

import os

import pytest

from .test_compatible_exe import runcode
from julia.core import raise_separate_cache_error

try:
    from types import SimpleNamespace
except ImportError:
    from argparse import Namespace as SimpleNamespace  # Python 2


def dummy_juliainfo():
    somepath = os.devnull  # some random path
    return SimpleNamespace(
        python=somepath,
        libpython_path=somepath,
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


@pytest.mark.pyjulia__using_default_setup
@pytest.mark.julia
def test_atexit():
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
        ''',
    )
    assert "atexit called" in proc.stdout

import os
from pathlib import Path
from subprocess import check_call

import pytest

from .test_compatible_exe import runcode


def test_trace_file_created(tmpdir):
    currdir = os.getcwd()
    os.chdir(str(tmpdir))
    runcode(
        """
    from julia.api import Julia
    jl = Julia(trace_compile="trace_compile.jl")

    from julia import Main
    Main.sin(2.0)
    """
    )
    os.chdir(currdir)
    assert (Path(tmpdir) / "trace_compile.jl").exists()

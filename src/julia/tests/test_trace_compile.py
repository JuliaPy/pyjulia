import os
from pathlib import Path
from subprocess import check_call

import pytest

from .test_compatible_exe import runcode


def test_trace_file_created(tmpdir):
    trace_compile_path = Path(tmpdir) / "trace_compile.jl"
    runcode(
        """
    from julia.api import Julia
    jl = Julia(trace_compile="{}")

    from julia import Main
    Main.sin(2.0)
    """.format(
            str(trace_compile_path)
        )
    )
    assert (trace_compile_path).exists()
    assert len(trace_compile_path.read_text().strip()) > 0

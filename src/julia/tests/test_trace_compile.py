import re
from pathlib import Path

from .test_compatible_exe import runcode
from .utils import skip_in_windows


@skip_in_windows
def test_trace_file_created(tmpdir):
    trace_compile_path = Path(tmpdir) / "trace_compile.jl"
    runcode(
        f"""
    from julia.api import Julia
    jl = Julia(trace_compile="{trace_compile_path}")

    from julia import Main
    Main.sin(2.0)
    """.format(
            str(trace_compile_path)
        )
    )
    assert (trace_compile_path).exists()
    assert len(trace_compile_path.read_text().strip()) > 0

    # check whether the sin precompilation directive is included in the file
    trace_compile_content = Path(trace_compile_path).read_text().strip()
    lines = [x for x in trace_compile_content.split("\n") if len(x) > 0]
    expected_precompile_line = (
        r"precompile\(Tuple\{typeof\([A-Za-z]+\.sin\), Float64\}\)"
    )
    assert any(
        [re.match(expected_precompile_line, x) is not None for x in lines]
    )

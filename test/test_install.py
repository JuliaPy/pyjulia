import os

import pytest

from julia import install

import subprocess


@pytest.mark.skipif(
    os.environ.get("CI", "false").lower() != "true", reason="CI=true not set"
)
def test_rebuild_broken_pycall(juliainfo):
    if juliainfo.version_info < (0, 7):
        pytest.skip("Julia >= 0.7 required")

    subprocess.call(
        [
            juliainfo.julia,
            "--startup-file=no",
            "-e",
            """using Pkg; Pkg.develop("PyCall")""",
        ]
    )

    # Remove ~/.julia/dev/PyCall/deps/deps.jl
    depsjl = os.path.join(
        os.path.expanduser("~"), ".julia", "dev", "PyCall", "deps", "deps.jl"
    )
    if os.path.exists(depsjl):
        print("Removing", depsjl)
        os.remove(depsjl)

    install(julia=juliainfo.julia)

    assert os.path.exists(depsjl)

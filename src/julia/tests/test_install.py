import os

import pytest

from julia import install

import subprocess

only_in_ci = pytest.mark.skipif(
    os.environ.get("CI", "false").lower() != "true", reason="CI=true not set"
)
"""
Tests that are too destructive to run with casual `tox` call.
"""


@only_in_ci
def test_noop(juliainfo):
    install(julia=juliainfo.julia)


@only_in_ci
def test_rebuild_broken_pycall(juliainfo):
    if juliainfo.version_info < (0, 7):
        pytest.skip("Julia >= 0.7 required")

    subprocess.check_call(
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

    # julia.install() should fix it:
    install(julia=juliainfo.julia)

    assert os.path.exists(depsjl)


@only_in_ci
def test_add_pycall(juliainfo):
    if juliainfo.version_info < (0, 7):
        pytest.skip("Julia >= 0.7 required")

    # Try to remove PyCall
    subprocess.call(
        [juliainfo.julia, "--startup-file=no", "-e", """using Pkg; Pkg.rm("PyCall")"""]
    )

    # julia.install() should add PyCall:
    install(julia=juliainfo.julia)

import os
import subprocess

import pytest

from julia.core import JuliaInfo, which


def dummy_juliainfo(**kwargs):
    defaults = dict(
        julia="julia",
        bindir="/dummy/bin",
        libjulia_path="/dummy/libjulia.so",
        sysimage="/dummy/sys.so",
        version_raw="1.1.1",
        version_major="1",
        version_minor="1",
        version_patch="1",
    )
    return JuliaInfo(**dict(defaults, **kwargs))


def check_core_juliainfo(jlinfo):
    assert os.path.exists(jlinfo.bindir)
    assert os.path.exists(jlinfo.libjulia_path)
    assert os.path.exists(jlinfo.sysimage)


def test_juliainfo_normal():
    jlinfo = JuliaInfo.load(os.getenv("PYJULIA_TEST_RUNTIME", "julia"))
    check_core_juliainfo(jlinfo)
    assert os.path.exists(jlinfo.python)
    # Note: jlinfo.libpython is probably not a full path so we are not
    # testing it here.


def test_is_compatible_exe_without_pycall():
    jlinfo = dummy_juliainfo()
    jlinfo.libpython_path = None
    assert not jlinfo.is_compatible_python()


def test_juliainfo_without_pycall(tmpdir):
    """
    `juliainfo` should not fail even when PyCall.jl is not installed.
    """

    runtime = os.getenv("PYJULIA_TEST_RUNTIME", "julia")

    depot = subprocess.check_output(
        [
            runtime,
            "--startup-file=no",
            "-e",
            """
            paths = [ARGS[1], DEPOT_PATH[2:end]...]
            print(join(paths, Sys.iswindows() ? ';' : ':'))
            """,
            str(tmpdir),
        ],
        universal_newlines=True,
    ).strip()

    jlinfo = JuliaInfo.load(runtime, env=dict(os.environ, JULIA_DEPOT_PATH=depot))

    check_core_juliainfo(jlinfo)
    assert jlinfo.python is None
    assert jlinfo.libpython_path is None
    assert not jlinfo.is_pycall_built()
    assert not jlinfo.is_compatible_python()


@pytest.mark.skipif(not which("false"), reason="false command not found")
def test_juliainfo_failure():
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        JuliaInfo.load(julia="false")
    assert excinfo.value.cmd[0] == "false"
    assert excinfo.value.returncode == 1
    assert isinstance(excinfo.value.output, str)

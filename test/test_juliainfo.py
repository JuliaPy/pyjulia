import os
import subprocess

from julia.core import juliainfo, _enviorn


def check_core_juliainfo(jlinfo):
    assert os.path.exists(jlinfo.JULIA_HOME)
    assert os.path.exists(jlinfo.libjulia_path)
    assert os.path.exists(jlinfo.image_file)


def test_juliainfo_normal():
    jlinfo = juliainfo(os.getenv("JULIA_EXE", "julia"))
    check_core_juliainfo(jlinfo)
    assert os.path.exists(jlinfo.pyprogramname)
    # Note: jlinfo.libpython is probably not a full path so we are not
    # testing it here.


def test_juliainfo_without_pycall(tmpdir):
    """
    `juliainfo` should not fail even when PyCall.jl is not installed.
    """

    runtime = os.getenv("JULIA_EXE", "julia")

    JULIA_DEPOT_PATH = subprocess.check_output(
        [runtime, "-e", """
        paths = [ARGS[1], DEPOT_PATH[2:end]...]
        print(join(paths, Sys.iswindows() ? ';' : ':'))
        """, str(tmpdir)],
        env=_enviorn,
        universal_newlines=True)

    jlinfo = juliainfo(
        runtime,
        env=dict(_enviorn, JULIA_DEPOT_PATH=JULIA_DEPOT_PATH))

    check_core_juliainfo(jlinfo)
    assert jlinfo.pyprogramname is None
    assert jlinfo.libpython is None

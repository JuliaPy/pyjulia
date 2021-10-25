import os
import shutil
from subprocess import check_call

import pytest

from julia.sysimage import build_sysimage

from ..tools import build_pycall
from .test_compatible_exe import runcode
from .utils import only_in_ci, skip_in_apple, skip_in_windows


def skip_early_julia_versions(juliainfo):
    if juliainfo.version_info < (1, 3, 1):
        pytest.skip("Julia < 1.3.1 is not supported")


def skip_julia_nightly(juliainfo):
    if juliainfo.version_info >= (1, 8):
        pytest.skip("custom sysimage with Julia >= 1.8 (nightly) is not supported")


def assert_sample_julia_code_runs(juliainfo, sysimage_path):
    very_random_string = "4903dc03-950f-4a54-98a3-c57a354b62df"
    proc = runcode(
        """
        from julia.api import Julia

        sysimage_path = {sysimage_path!r}
        very_random_string = {very_random_string!r}
        jl = Julia(
            debug=True,
            sysimage=sysimage_path,
            runtime={juliainfo.julia!r},
        )

        from julia import Main
        Main.println(very_random_string)
        """.format(
            juliainfo=juliainfo,
            sysimage_path=sysimage_path,
            very_random_string=very_random_string,
        )
    )
    assert very_random_string in proc.stdout


@pytest.mark.julia
@only_in_ci
@skip_in_windows
@skip_in_apple
@pytest.mark.parametrize("with_pycall_cache", [False, True])
def test_build_and_load(tmpdir, juliainfo, with_pycall_cache):
    skip_early_julia_versions(juliainfo)
    skip_julia_nightly(juliainfo)

    if with_pycall_cache:
        build_pycall(julia=juliainfo.julia)
        check_call([juliainfo.julia, "--startup-file=no", "-e", "using PyCall"])
    else:
        # TODO: don't remove user's compile cache
        cachepath = os.path.join(
            os.path.expanduser("~"),
            ".julia",
            "compiled",
            "v{}.{}".format(juliainfo.version_major, juliainfo.version_minor),
            "PyCall",
        )
        shutil.rmtree(cachepath)

    sysimage_path = str(tmpdir.join("sys.so"))
    build_sysimage(sysimage_path, julia=juliainfo.julia)

    assert_sample_julia_code_runs(juliainfo, sysimage_path)


@pytest.mark.julia
@only_in_ci
@skip_in_windows  # Avoid "LVM ERROR: out of memory"
@skip_in_apple
def test_build_with_basesysimage_and_load(tmpdir, juliainfo):
    skip_early_julia_versions(juliainfo)
    skip_julia_nightly(juliainfo)

    sysimage_path = str(tmpdir.join("sys.so"))
    base_sysimage_path = juliainfo.sysimage
    build_sysimage(
        sysimage_path, julia=juliainfo.julia, base_sysimage=base_sysimage_path
    )

    assert_sample_julia_code_runs(juliainfo, sysimage_path)

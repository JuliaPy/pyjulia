import pytest

from .test_compatible_exe import runcode
from julia.sysimage import build_sysimage


@pytest.mark.julia
def test_build_and_load(tmpdir, juliainfo):
    if juliainfo.version_info < (0, 7):
        pytest.skip("Julia < 0.7 is not supported")

    sysimage_path = str(tmpdir.join("sys.so"))
    build_sysimage(sysimage_path, julia=juliainfo.julia)

    runcode(
        """
        from julia.api import Julia

        sysimage_path = {!r}
        jl = Julia(sysimage=sysimage_path)
        """.format(
            sysimage_path
        )
    )

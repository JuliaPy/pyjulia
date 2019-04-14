import pytest

from julia.sysimage import build_sysimage

from .test_compatible_exe import runcode
from .utils import only_in_ci, skip_in_appveyor


@pytest.mark.julia
@only_in_ci
@skip_in_appveyor  # Avoid "LVM ERROR: out of memory"
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

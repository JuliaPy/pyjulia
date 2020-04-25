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

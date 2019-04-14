import pytest

from julia.core import JuliaInfo

from .test_compatible_exe import runcode

juliainfo = JuliaInfo.load()


@pytest.mark.skipif("juliainfo.version_info < (0, 7)")
@pytest.mark.julia
def test_compiled_modules_no():
    runcode(
        """
        from julia.core import Julia

        Julia(debug=True, compiled_modules=False)

        from julia import Main
        use_compiled_modules = Main.eval("Base.JLOptions().use_compiled_modules")

        print("use_compiled_modules =", use_compiled_modules)
        assert use_compiled_modules == 0
        """,
        check=True,
    )


@pytest.mark.skipif("not juliainfo.is_compatible_python()")
@pytest.mark.julia
def test_custom_sysimage(tmpdir):
    sysimage = str(tmpdir.join("sys.so"))
    runcode(
        """
        from shutil import copyfile
        from julia.core import LibJulia, JuliaInfo, enable_debug

        enable_debug()
        info = JuliaInfo.load()

        sysimage = {!r}
        copyfile(info.sysimage, sysimage)

        api = LibJulia.load()
        api.init_julia(["--sysimage", sysimage])

        from julia import Main
        actual = Main.eval("unsafe_string(Base.JLOptions().image_file)")

        print("actual =", actual)
        print("sysimage =", sysimage)
        assert actual == sysimage
        """.format(
            sysimage
        ),
        check=True,
    )


@pytest.mark.julia
def test_non_existing_sysimage(tmpdir):
    proc = runcode(
        """
        import sys
        from julia.core import enable_debug, LibJulia

        enable_debug()

        api = LibJulia.load()
        try:
            api.init_julia(["--sysimage", "sys.so"])
        except RuntimeError as err:
            print(err)
            assert "System image" in str(err)
            assert "does not exist" in str(err)
            sys.exit(55)
        """,
        cwd=str(tmpdir),
    )
    assert proc.returncode == 55

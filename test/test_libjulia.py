import sys

from .test_compatible_exe import runcode


def test_custom_sysimage(tmpdir):
    sysimage = str(tmpdir.join("sys.so"))
    runcode(
        sys.executable,
        """
        from shutil import copyfile
        from julia.core import LibJulia, JuliaInfo, enable_debug

        enable_debug()
        info = JuliaInfo.load()

        sysimage = {!r}
        copyfile(info.image_file, sysimage)

        api = LibJulia.load()
        api.init_julia(["--sysimage", sysimage])

        from julia import Main
        actual = Main.eval("unsafe_string(Base.JLOptions().image_file)")

        print("actual =", actual)
        print("sysimage =", sysimage)
        assert actual == sysimage
        """.format(sysimage),
        check=True)

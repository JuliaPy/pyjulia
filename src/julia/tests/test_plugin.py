import os

import pytest

from julia.core import which

pytest_plugins = ["pytester"]

is_windows = os.name == "nt"
userhome = os.path.expanduser("~")


def test__using_default_setup(testdir, request, monkeypatch):
    if request.config.getoption("runpytest") != "subprocess":
        raise ValueError("Need `-p pytester --runpytest=subprocess` options.")
    monkeypatch.delenv("PYJULIA_TEST_RUNTIME", raising=False)

    # create a temporary conftest.py file
    testdir.makeini(
        """
        [pytest]
        addopts =
            -p julia.pytestplugin
        """
    )

    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.pyjulia__using_default_setup
        def test():
            pass
        """
    )

    args = ("-p", "julia.pytestplugin", "--no-julia")
    r0 = testdir.runpytest(*args)
    r0.assert_outcomes(passed=1)

    r1 = testdir.runpytest("--julia-runtime", which("julia"), *args)
    r1.assert_outcomes(skipped=1)

    r2 = testdir.runpytest("--julia-inline=yes", *args)
    r2.assert_outcomes(skipped=1)


@pytest.mark.skipif(
    is_windows, reason="cannot run on Windows; symlink is used inside test"
)
def test_undo_no_julia(testdir, request):
    if request.config.getoption("runpytest") != "subprocess":
        raise ValueError("Need `-p pytester --runpytest=subprocess` options.")

    # TODO: Support `JULIA_DEPOT_PATH`; or a better approach would be
    # to not depend on user's depot at all.
    testdepot = os.path.join(str(testdir.tmpdir), ".julia")
    userdepot = os.path.join(userhome, ".julia")
    os.symlink(userdepot, testdepot)

    # create a temporary conftest.py file
    testdir.makeini(
        """
        [pytest]
        addopts =
            -p julia.pytestplugin --no-julia
        """
    )

    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.julia
        def test():
            pass
        """
    )

    r0 = testdir.runpytest()
    r0.assert_outcomes(skipped=1)

    r1 = testdir.runpytest("--julia")
    r1.assert_outcomes(passed=1)

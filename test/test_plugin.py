from julia.core import which


pytest_plugins = ["pytester"]


def test__using_default_setup(testdir):
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

    args = ("-p", "julia.pytestplugin")
    r0 = testdir.runpytest(*args)
    r0.assert_outcomes(passed=1)

    r1 = testdir.runpytest("--julia-runtime", which("julia"), *args)
    r1.assert_outcomes(skipped=1)

    r2 = testdir.runpytest("--julia-inline=yes", *args)
    r2.assert_outcomes(skipped=1)

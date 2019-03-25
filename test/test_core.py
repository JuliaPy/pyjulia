from __future__ import print_function

import array
import math
import subprocess
from types import ModuleType

from julia import JuliaError
from julia.core import jl_name, py_name, _enviorn as orig_env
import sys

import pytest

python_version = sys.version_info


def test_call(julia):
    julia._call("1 + 1")
    julia._call("sqrt(2.0)")


def test_eval(julia):
    assert julia.eval("1 + 1") == 2
    assert julia.eval("sqrt(2.0)") == math.sqrt(2.0)
    assert julia.eval("PyObject(1)") == 1
    assert julia.eval("PyObject(1000)") == 1000
    assert julia.eval("PyObject((1, 2, 3))") == (1, 2, 3)


def test_call_error(julia):
    msg = "Error with message"
    with pytest.raises(JuliaError) as excinfo:
        julia._call('error("{}")'.format(msg))
    assert msg in str(excinfo.value)


def test_call_julia_function_with_python_args(Main):
    assert list(Main.map(Main.uppercase, array.array("u", [u"a", u"b", u"c"]))) == [
        "A",
        "B",
        "C",
    ]
    assert list(Main.map(Main.floor, [1.1, 2.2, 3.3])) == [1.0, 2.0, 3.0]
    assert Main.cos(0) == 1.0


def test_call_julia_with_python_callable(Main):
    def add(a, b):
        return a + b

    assert list(Main.map(lambda x: x * x, [1, 2, 3])) == [1, 4, 9]
    assert all(
        x == y
        for x, y in zip(
            [11, 11, 11], Main.map(lambda x: x + 1, array.array("I", [10, 10, 10]))
        )
    )
    assert Main.reduce(add, [1, 2, 3]) == 6


def test_call_python_with_julia_args(julia):
    assert sum(julia.eval("(1, 2, 3)")) == 6
    assert list(map(julia.eval("x->x^2"), [1, 2, 3])) == [1, 4, 9]


def test_import_julia_functions(julia):
    if python_version.major < 3 or (
        python_version.major == 3 and python_version.minor < 3
    ):
        import julia.sum as julia_sum

        assert julia_sum([1, 2, 3]) == 6
    else:
        pass


def test_import_julia_module_existing_function(julia):
    from julia import Base

    assert Base.mod(2, 2) == 0


def test_from_import_existing_julia_function(julia):
    from julia.Base import divrem

    assert divrem(7, 3) == (2, 1)


def test_import_julia_module_non_existing_name(julia):
    from julia import Base

    with pytest.raises(AttributeError):
        Base.spamspamspam


def test_from_import_non_existing_julia_name(julia):
    try:
        from Base import spamspamspam
    except ImportError:
        pass
    else:
        assert not spamspamspam


def test_julia_module_bang(julia):
    from julia.Base import Channel, put_b, take_b

    chan = Channel(1)
    sent = 123
    put_b(chan, sent)
    received = take_b(chan)
    assert sent == received


def test_import_julia_submodule(julia):
    from julia.Base import Enums

    assert isinstance(Enums, ModuleType)
    assert Enums.__name__ == "julia.Base.Enums"
    assert julia.fullname(Enums) == "Base.Enums"


def test_getattr_submodule(Main):
    assert Main._PyJuliaHelper.IOPiper.__name__ == "julia.Main._PyJuliaHelper.IOPiper"


def test_star_import_julia_module(julia):
    from . import _star_import

    _star_import.Enum


def test_main_module(julia, Main):
    Main.x = x = 123456
    assert julia.eval("x") == x


def test_module_all(julia):
    from julia import Base

    assert "resize_b" in Base.__all__


def test_module_dir(julia):
    from julia import Base

    assert "resize_b" in dir(Base)


@pytest.mark.skipif(
    "PYJULIA_TEST_RUNTIME" in orig_env,
    reason=(
        "cannot be tested with custom Julia executable;"
        " PYJULIA_TEST_RUNTIME is set to {}".format(
            orig_env.get("PYJULIA_TEST_RUNTIME")
        )
    ),
)
def test_import_without_setup():
    command = [sys.executable, "-c", "from julia import Base"]
    print("Executing:", *command)
    subprocess.check_call(command, env=orig_env)


# TODO: this causes a segfault
"""
def test_import_julia_modules(julia):
    import julia.PyCall as pycall
    assert pycall.pyeval('2 * 3') == 6
"""


@pytest.mark.parametrize("name", ["normal", "resize!"])
def test_jlpy_identity(name):
    assert jl_name(py_name(name)) == name


@pytest.mark.parametrize("name", ["normal", "resize_b"])
def test_pyjl_identity(name):
    assert py_name(jl_name(name)) == name

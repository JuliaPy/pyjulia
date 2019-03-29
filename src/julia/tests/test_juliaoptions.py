import pytest

from julia.core import JuliaOptions


# fmt: off
@pytest.mark.parametrize("kwargs, args", [
    ({}, []),
    (dict(compiled_modules=None), []),
    (dict(compiled_modules=False), ["--compiled-modules", "no"]),
    (dict(compiled_modules="no"), ["--compiled-modules", "no"]),
    (dict(depwarn="error"), ["--depwarn", "error"]),
    (dict(sysimage="PATH"), ["--sysimage", "PATH"]),
    (dict(bindir="PATH"), ["--home", "PATH"]),
])
# fmt: on
def test_as_args(kwargs, args):
    assert JuliaOptions(**kwargs).as_args() == args


@pytest.mark.parametrize("kwargs", [
    dict(compiled_modules="invalid value"),
    dict(bindir=123456789),
])
def test_valueerror(kwargs):
    with pytest.raises(ValueError) as excinfo:
        JuliaOptions(**kwargs)
    assert "Option" in str(excinfo.value)
    assert "accept" in str(excinfo.value)


# fmt: off
@pytest.mark.parametrize("kwargs", [
    dict(invalid_option=None),
    dict(invalid_option_1=None, invalid_option_2=None),
])
# fmt: on
def test_unsupported(kwargs):
    with pytest.raises(TypeError) as excinfo:
        JuliaOptions(**kwargs)
    assert "Unsupported Julia option(s): " in str(excinfo.value)
    for key in kwargs:
        assert key in str(excinfo.value)

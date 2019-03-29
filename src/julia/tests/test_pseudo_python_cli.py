import shlex

import pytest

from julia.pseudo_python_cli import parse_args


def make_dict(**kwargs):
    ns = parse_args([])
    return dict(vars(ns), **kwargs)


# fmt: off
@pytest.mark.parametrize("args, desired", [
    ("-m json.tool -h", make_dict(module="json.tool", args=["-h"])),
    ("-mjson.tool -h", make_dict(module="json.tool", args=["-h"])),
    ("-imjson.tool -h",
     make_dict(interactive=True, module="json.tool", args=["-h"])),
    ("-m ipykernel install --user --name NAME --display-name DISPLAY_NAME",
     make_dict(module="ipykernel",
               args=shlex.split("install --user --name NAME"
                                " --display-name DISPLAY_NAME"))),
    ("-m ipykernel_launcher -f FILE",
     make_dict(module="ipykernel_launcher",
               args=shlex.split("-f FILE"))),
    ("-", make_dict(script="-")),
    ("- a", make_dict(script="-", args=["a"])),
    ("script", make_dict(script="script")),
    ("script a", make_dict(script="script", args=["a"])),
    ("script -m", make_dict(script="script", args=["-m"])),
    ("script -c 1", make_dict(script="script", args=["-c", "1"])),
    ("script -h 1", make_dict(script="script", args=["-h", "1"])),
])
# fmt: on
def test_valid_args(args, desired):
    ns = parse_args(shlex.split(args))
    actual = vars(ns)
    assert actual == desired


# fmt: off
@pytest.mark.parametrize("args", [
    "-m",
    "-c",
    "-i -m",
    "-h -m",
    "-V -m",
])
# fmt: on
def test_invalid_args(args, capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(shlex.split(args))
    assert exc_info.value.code != 0

    captured = capsys.readouterr()
    assert "usage:" in captured.err
    assert not captured.out


# fmt: off
@pytest.mark.parametrize("args", [
    "-h",
    "-i --help",
    "-h -i",
    "-hi",
    "-ih",
    "-Vh",
    "-hV",
    "-h -m json.tool",
    "-h -mjson.tool",
])
# fmt: on
def test_help_option(args, capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(shlex.split(args))
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert not captured.err


# fmt: off
@pytest.mark.parametrize("args", [
    "-V",
    "--version",
    "-V -i",
    "-Vi",
    "-iV",
    "-V script",
    "-V script -h",
])
# fmt: on
def test_version_option(args, capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(shlex.split(args))
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "Python " in captured.out
    assert not captured.err

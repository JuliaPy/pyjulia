import shlex

import pytest

from julia.pseudo_python_cli import parse_args


def make_dict(**kwargs):
    ns = parse_args([])
    return dict(vars(ns), **kwargs)


@pytest.mark.parametrize("args, desired", [
    ("-m json.tool -h", make_dict(module="json.tool", args=["-h"])),
    ("-mjson.tool -h", make_dict(module="json.tool", args=["-h"])),
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
])
def test_valid_args(args, desired):
    ns = parse_args(shlex.split(args))
    actual = vars(ns)
    assert actual == desired


@pytest.mark.parametrize("args", [
    "-m",
    "-c",
    "-i -m",
    # They are invalid in python CLI but works in argparse (which is
    # probably OK):
    pytest.mark.xfail("-V -m"),
    pytest.mark.xfail("-h -m"),
])
def test_invalid_args(args, capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(shlex.split(args))
    assert exc_info.value.code != 0

    captured = capsys.readouterr()
    assert "usage:" in captured.err


@pytest.mark.parametrize("cli_args", [
    ["-h"],
    ["-i", "--help"],
    ["-h", "-i"],
    ["-hi"],
    ["-ih"],
    ["-h", "-m", "json.tool"],
    ["-h", "-mjson.tool"],
])
def test_help_option(cli_args, capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(cli_args)
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out

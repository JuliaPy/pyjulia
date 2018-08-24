from IPython.testing.globalipapp import get_ipython
import pytest

from julia.core import Julia
from julia.magic import JuliaCompleter
import julia.magic

try:
    from types import SimpleNamespace
except ImportError:
    from argparse import Namespace as SimpleNamespace  # Python 2

try:
    string_types = (unicode, str)
except NameError:
    string_types = (str,)


def get_julia_magics():
    return julia.magic.JuliaMagics(shell=get_ipython())


def test_register_magics():
    julia.magic.load_ipython_extension(get_ipython())


def test_success_line():
    jm = get_julia_magics()
    ans = jm.julia('1')
    assert ans == 1


def test_success_cell():
    jm = get_julia_magics()
    ans = jm.julia(None, '2')
    assert ans == 2


def test_failure_line():
    jm = get_julia_magics()
    ans = jm.julia('pop!([])')
    assert ans is None


def test_failure_cell():
    jm = get_julia_magics()
    ans = jm.julia(None, '1 += 1')
    assert ans is None


def make_event(line, text_until_cursor=None, symbol=""):
    if text_until_cursor is None:
        text_until_cursor = line
    return SimpleNamespace(
        line=line,
        text_until_cursor=text_until_cursor,
        symbol=symbol,
    )


completable_events = [
    make_event("%julia "),
    make_event("%julia si"),
    make_event("%julia Base.si"),
]

uncompletable_events = [
    make_event(""),
    make_event("%julia si", text_until_cursor="%ju"),
]


def check_version():
    julia = Julia()
    if julia.eval('VERSION < v"0.7-"'):
        raise pytest.skip("Completion not supported in Julia 0.6")


@pytest.mark.parametrize("event", completable_events)
def test_completable_events(event):
    jc = JuliaCompleter()
    dummy_ipython = None
    completions = jc.complete_command(dummy_ipython, event)
    assert isinstance(completions, list)
    check_version()
    assert set(map(type, completions)) <= set(string_types)


@pytest.mark.parametrize("event", uncompletable_events)
def test_uncompletable_events(event):
    jc = JuliaCompleter()
    dummy_ipython = None
    completions = jc.complete_command(dummy_ipython, event)
    assert isinstance(completions, list)
    assert not completions

from IPython.testing.globalipapp import get_ipython
from julia import magic
import pytest


@pytest.fixture
def julia_magics(julia):
    return magic.JuliaMagics(shell=get_ipython())


def test_register_magics(julia):
    magic.load_ipython_extension(get_ipython())


def test_success_line(julia_magics):
    ans = julia_magics.julia('1')
    assert ans == 1


def test_success_cell(julia_magics):
    ans = julia_magics.julia(None, '2')
    assert ans == 2


def test_failure_line(julia_magics):
    ans = julia_magics.julia('pop!([])')
    assert ans is None


def test_failure_cell(julia_magics):
    ans = julia_magics.julia(None, '1 += 1')
    assert ans is None

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


def test_revise_error():
    from julia.ipy import revise

    counter = [0]

    def throw():
        counter[0] += 1
        raise RuntimeError("fake revise error")

    revise_wrapper = revise.make_revise_wrapper(throw)

    revise.revise_errors = 0
    try:
        assert revise.revise_errors_limit == 1

        with pytest.warns(UserWarning) as record1:
            revise_wrapper()  # called
        assert len(record1) == 2
        assert "fake revise error" in record1[0].message.args[0]
        assert "Turning off Revise.jl" in record1[1].message.args[0]

        revise_wrapper()  # not called

        assert counter[0] == 1
        assert revise.revise_errors == 1
    finally:
        revise.revise_errors = 0

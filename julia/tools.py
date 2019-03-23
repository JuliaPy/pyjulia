from __future__ import print_function, absolute_import

import sys


def make_receiver(io):
    def receiver(s):
        io.write(s)
        io.flush()

    return receiver


def redirect_output_streams():
    """
    Redirect Julia's stdout and stderr to Python's counter parts.
    """

    from .Main._PyJuliaHelper.IOPiper import pipe_std_outputs

    pipe_std_outputs(make_receiver(sys.stdout), make_receiver(sys.stderr))

    # TODO: Invoking `redirect_output_streams()` in terminal IPython
    # terminates the whole Python process.  Find out why.

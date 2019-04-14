"""
Python interpreter inside a Julia process.

This command line interface mimics a basic subset of Python program so that
Python program involving calls to Julia functions can be run in a *Julia*
process.  This avoids the known problem with pre-compilation cache in
Debian-based distribution such as Ubuntu and Python executable installed by
Conda in Linux.

Although this script has -i option and it can do a basic REPL, contrl-c may
crash the whole process.  Consider using IPython >= 7 which can be launched
by::

    python-jl -m IPython

.. NOTE::

   For this command to work, Python environment with which PyCall.jl is
   configured has to have PyJulia installed.
"""

from __future__ import absolute_import, print_function

import sys

from .pseudo_python_cli import ARGUMENT_HELP, make_parser, parse_args_with
from .utils import execprog

PYJL_ARGUMENT_HELP = (
    ARGUMENT_HELP
    + """
  --julia JULIA  Julia runtime to be used. (default: julia)
"""
)

script_jl = """
import PyCall

let code = PyCall.pyimport("julia.pseudo_python_cli")[:main](ARGS)
    if code isa Integer
        exit(code)
    end
end
"""


def remove_julia_options(args):
    """
    Remove options used in this Python process.

    >>> list(remove_julia_options(["a", "b", "c"]))
    ['a', 'b', 'c']
    >>> list(remove_julia_options(["a", "--julia", "julia", "b", "c"]))
    ['a', 'b', 'c']
    >>> list(remove_julia_options(["a", "b", "c", "--julia=julia"]))
    ['a', 'b', 'c']
    """
    it = iter(args)
    for a in it:
        if a == "--julia":
            try:
                next(it)
            except StopIteration:
                return
            continue
        elif a.startswith("--julia="):
            continue
        yield a


def parse_pyjl_args(args):
    """
    Return a pair of parsed result and "unused" arguments.

    Returns
    -------
    ns : argparse.Namespace
        Parsed result.  Only `ns.julia` is relevant here.
    unused_args : list
        Arguments to be parsed (again) by `.pseudo_python_cli.main`.

    Examples
    --------
    >>> ns, unused_args = parse_pyjl_args([])
    >>> ns.julia
    'julia'
    >>> unused_args
    []
    >>> ns, unused_args = parse_pyjl_args(
    ...     ["--julia", "julia-dev", "-i", "-c", "import julia"])
    >>> ns.julia
    'julia-dev'
    >>> unused_args
    ['-i', '-c', 'import julia']
    """
    # Mix the options we need in this Python process with the Python
    # arguments to be parsed in the "subprocess".  This way, we get a
    # parse error right now without initializing Julia runtime and
    # importing PyCall.jl etc. to get an extra speedup for the
    # abnormal case (including -h/--help and -V/--version).
    parser = make_parser(description=__doc__ + PYJL_ARGUMENT_HELP)
    parser.add_argument("--julia", default="julia")

    ns = parse_args_with(parser, args)
    unused_args = list(remove_julia_options(args))
    return ns, unused_args


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    ns, unused_args = parse_pyjl_args(args)
    julia = ns.julia
    execprog([julia, "-e", script_jl, "--"] + unused_args)


if __name__ == "__main__":
    main()

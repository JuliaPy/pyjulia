from __future__ import print_function, absolute_import

from argparse import Namespace
import sys

from .api import LibJulia


def parse_args(args):
    ns = Namespace(julia="julia")
    jl_args = list(args)

    if len(jl_args) >= 2 and jl_args[0] == "--julia":
        ns.julia = jl_args[1]
        jl_args = jl_args[2:]
    elif len(jl_args) >= 1 and jl_args[0].startswith("--julia="):
        ns.julia = jl_args[0][len("--julia=") :]
        jl_args = jl_args[1:]

    return ns, jl_args


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    ns, jl_args = parse_args(args)

    api = LibJulia.load(julia=ns.julia)
    api.init_julia(jl_args)
    code = int(not api.jl_eval_string(b"Base._start()"))
    api.jl_atexit_hook(code)
    sys.exit(code)


if __name__ == "__main__":
    main()

"""
(Maybe) Re-build PyCall.jl to test ``exe_differs=False`` path.

``Pkg.build("PyCall")`` is run on Julia side when the environment
variable `PYJULIA_TEST_REBUILD` is set to ``yes``.
"""

from __future__ import print_function, absolute_import

import os
import subprocess
import sys
from contextlib import contextmanager

from .core import juliainfo


@contextmanager
def maybe_rebuild(rebuild, julia):
    if rebuild:
        env = os.environ.copy()
        info = juliainfo(julia)

        build = [julia, '-e', 'Pkg.build("PyCall")']
        print('Building PyCall.jl with PYTHON =', sys.executable)
        print(*build)
        subprocess.check_call(build, env=dict(env, PYTHON=sys.executable))
        try:
            yield
        finally:
            print('Restoring previous PyCall.jl build...')
            print(*build)
            if info.pyprogramname:
                env = dict(env, PYTHON=info.pyprogramname)
            if 'PYTHON' in env:
                print('PYTHON =', env['PYTHON'])
            subprocess.check_call(build, env=env)
    else:
        yield


def with_rebuilt(rebuild, julia, command):
    with maybe_rebuild(rebuild, julia):
        print('Execute:', *command)
        return subprocess.call(command)


def main(args=None):
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__)
    parser.add_argument(
        '--rebuild', default=os.getenv('PYJULIA_TEST_REBUILD', 'no'),
        choices=('yes', 'no'),
        help="""
        """)
    parser.add_argument(
        '--julia', default=os.getenv('JULIA_EXE', 'julia'),
        help="""
        Julia executable to be used.
        Default to the value of environment variable JULIA_EXE if set.
        """)
    parser.add_argument(
        'command', nargs='+',
        help='Command and arguments to run.')
    ns = parser.parse_args(args)
    ns.rebuild = ns.rebuild == 'yes'
    sys.exit(with_rebuilt(**vars(ns)))


if __name__ == '__main__':
    main()

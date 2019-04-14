"""
Pseudo Python command line interface.

It tries to mimic a subset of Python CLI:
https://docs.python.org/3/using/cmdline.html
"""

from __future__ import absolute_import, print_function

import code
import copy
import runpy
import sys
import traceback
from collections import namedtuple

try:
    from types import SimpleNamespace
except ImportError:
    from argparse import Namespace as SimpleNamespace


ARGUMENT_HELP = """
positional arguments:
  script         path to file (default: None)
  args           arguments passed to program in sys.argv[1:]

optional arguments:
  -h, --help     show this help message and exit
  -i             inspect interactively after running script.
  --version, -V  Print the Python version number and exit.
                 -VV is not supported.
  -c COMMAND     Execute the Python code in COMMAND.
  -m MODULE      Search sys.path for the named MODULE and execute its contents
                 as the __main__ module.
"""


def python(module, command, script, args, interactive):
    if command:
        sys.argv[0] = "-c"

    assert sys.argv
    sys.argv[1:] = args
    if script:
        sys.argv[0] = script

    banner = ""
    try:
        if command:
            scope = {}
            exec(command, scope)
        elif module:
            scope = runpy.run_module(module, run_name="__main__", alter_sys=True)
        elif script == "-":
            source = sys.stdin.read()
            exec(compile(source, "<stdin>", "exec"), scope)
        elif script:
            scope = runpy.run_path(script, run_name="__main__")
        else:
            interactive = True
            scope = None
            banner = None  # show banner
    except Exception:
        if not interactive:
            raise
        traceback.print_exc()

    if interactive:
        code.interact(banner=banner, local=scope)


ArgDest = namedtuple("ArgDest", "dest names default")
Optional = namedtuple("Optional", "name is_long argdest nargs action terminal")
Result = namedtuple("Result", "option values")


class PyArgumentParser(object):

    """
    `ArgumentParser`-like parser with "terminal option" support.

    Major differences:

    * Formatted help has to be provided to `description`.
    * Many options for `.add_argument` are not supported.
    * Especially, there is no positional argument support: all positional
      arguments go into `ns.args`.
    * `.add_argument` can take boolean option `terminal` (default: `False`)
      to stop parsing after consuming the given option.
    """

    def __init__(self, prog=None, usage="%(prog)s [options] [args]", description=""):
        self.prog = sys.argv[0] if prog is None else prog
        self.usage = usage
        self.description = description

        self._dests = ["args"]
        self._argdests = [ArgDest("args", (), [])]
        self._options = []

        self.add_argument("--help", "-h", "-?", action="store_true")

    def format_usage(self):
        return "usage: " + self.usage % {"prog": self.prog}

    # Once we drop Python 2, we can do:
    """
    def add_argument(self, name, *alt, dest=None, nargs=None, action=None,
                     default=None, terminal=False):
    """

    def add_argument(self, name, *alt, **kwargs):
        return self._add_argument_impl(name, alt, **kwargs)

    # fmt: off

    def _add_argument_impl(self, name, alt, dest=None, nargs=None, action=None,
                           default=None, terminal=False):
        if dest is None:
            if name.startswith("--"):
                dest = name[2:]
            elif not name.startswith("-"):
                dest = name
            else:
                raise ValueError(name)

        if not name.startswith("-"):
            raise NotImplementedError(
                "Positional arguments are not supported."
                " All positional arguments will be stored in `ns.args`.")
        if terminal and action is not None:
            raise NotImplementedError(
                "Terminal option is assumed to have argument."
                " Non-`None` action={} is not supported".format())

        if nargs is not None and action is not None:
            raise TypeError("`nargs` and `action` are mutually exclusive")
        if action == "store_true":
            nargs = 0
        assert nargs is None or isinstance(nargs, int)
        assert action in (None, "store_true")

        assert dest not in self._dests
        self._dests.append(dest)

        argdest = ArgDest(
            dest=dest,
            names=(name,) + alt,
            default=default,
        )
        self._argdests.append(argdest)

        for arg in (name,) + alt:
            self._options.append(Optional(
                name=arg,
                is_long=arg.startswith("--"),
                argdest=argdest,
                nargs=nargs,
                action=action,
                terminal=terminal,
            ))

    def parse_args(self, args):
        ns = SimpleNamespace(**{
            argdest.dest: copy.copy(argdest.default)
            for argdest in self._argdests
        })
        args_iter = iter(args)
        self._parse_until_terminal(ns, args_iter)
        ns.args.extend(args_iter)

        if ns.help:
            self.print_help()
            self.exit()
        del ns.help

        return ns

    def _parse_until_terminal(self, ns, args_iter):
        seen = set()
        for a in args_iter:

            results = self._find_matches(a)
            if not results:
                ns.args.append(a)
                break

            for i, res in enumerate(results):
                dest = res.option.argdest.dest
                if dest in seen:
                    self._usage_and_error(
                        "{} provided more than twice"
                        .format(", ".join(res.option.argdest.names)))
                seen.add(dest)

                num_args = res.option.nargs
                if num_args is None:
                    num_args = 1
                while len(res.values) < num_args:
                    try:
                        res.values.append(next(args_iter))
                    except StopIteration:
                        self.error(self.format_usage())

                if res.option.action == "store_true":
                    setattr(ns, dest, True)
                else:
                    value = res.values
                    if res.option.nargs is None:
                        value, = value
                    setattr(ns, dest, value)

                if res.option.terminal:
                    assert i == len(results) - 1
                    return

    def _find_matches(self, arg):
        """
        Return a list of `.Result`.

        If value presents in `arg` (i.e., ``--long-option=value``), it
        becomes the element of `.Result.values` (a list).  Otherwise,
        this list has to be filled by the caller (`_parse_until_terminal`).
        """
        for opt in self._options:
            if arg == opt.name:
                return [Result(opt, [])]
            elif arg.startswith(opt.name):
                # i.e., len(arg) > len(opt.name):
                if opt.is_long and arg[len(opt.name)] == "=":
                    return [Result(opt, [arg[len(opt.name) + 1:]])]
                elif not opt.is_long:
                    if opt.nargs != 0:
                        return [Result(opt, [arg[len(opt.name):]])]
                    else:
                        results = [Result(opt, [])]
                        rest = "-" + arg[len(opt.name):]
                        results.extend(self._find_matches(rest))
                        return results
                        # arg="-ih" -> rest="-h"
        return []
    # fmt: on

    def print_usage(self, file=None):
        print(self.format_usage(), file=file or sys.stdout)

    def print_help(self):
        self.print_usage()
        print()
        print(self.description)

    def exit(self, status=0):
        sys.exit(status)

    def _usage_and_error(self, message):
        self.print_usage(sys.stderr)
        print(file=sys.stderr)
        self.error(message)

    def error(self, message):
        print(message, file=sys.stderr)
        self.exit(2)


def make_parser(description=__doc__ + ARGUMENT_HELP):
    parser = PyArgumentParser(
        prog=None if sys.argv[0] else "python",
        usage="%(prog)s [option] ... [-c cmd | -m mod | script | -] [args]",
        description=description,
    )

    parser.add_argument("-i", dest="interactive", action="store_true")
    parser.add_argument("--version", "-V", action="store_true")
    parser.add_argument("-c", dest="command", terminal=True)
    parser.add_argument("-m", dest="module", terminal=True)

    return parser


def parse_args_with(parser, args):
    ns = parser.parse_args(args)

    if ns.command and ns.module:
        parser.error("-c and -m are mutually exclusive")
    if ns.version:
        print("Python {0}.{1}.{2}".format(*sys.version_info))
        parser.exit()
    del ns.version

    ns.script = None
    if (not (ns.command or ns.module)) and ns.args:
        ns.script = ns.args[0]
        ns.args = ns.args[1:]

    return ns


def parse_args(args):
    return parse_args_with(make_parser(), args)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    try:
        ns = parse_args(args)
        python(**vars(ns))
    except SystemExit as err:
        return err.code
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

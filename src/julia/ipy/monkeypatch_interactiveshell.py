"""
Monkey-patch `TerminalInteractiveShell` to highlight code in ``%%julia``.
"""

from __future__ import absolute_import, print_function

from IPython.terminal.interactiveshell import TerminalInteractiveShell
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import JuliaLexer


class TerminalInteractiveShellPatcher(object):
    def __init__(self):
        self.patch_extra_prompt_options(TerminalInteractiveShell)

    def patch_extra_prompt_options(self, TerminalInteractiveShell):
        orig__extra_prompt_options = TerminalInteractiveShell._extra_prompt_options
        self.orig__extra_prompt_options = orig__extra_prompt_options

        def _extra_prompt_options(self):
            options = orig__extra_prompt_options(self)
            options["lexer"].magic_lexers["julia"] = PygmentsLexer(JuliaLexer)
            return options

        TerminalInteractiveShell._extra_prompt_options = _extra_prompt_options


# Make it work with reload:
try:
    PATCHER
except NameError:
    PATCHER = None


def patch_interactiveshell(ip):
    global PATCHER
    if PATCHER is not None:
        return
    if isinstance(ip, TerminalInteractiveShell):
        PATCHER = TerminalInteractiveShellPatcher()


# TODO: write `unpatch_interactiveshell`

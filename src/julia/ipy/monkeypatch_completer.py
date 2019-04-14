"""
Monkey-patch `IPCompleter` to make code completion work in ``%%julia``.

This is done by monkey-patching because it looks like there is no
immediate plan for an API to do this:
https://github.com/ipython/ipython/pull/10722
"""

from __future__ import absolute_import, print_function

import re

from IPython.core.completer import Completion, IPCompleter


class JuliaCompleter(object):
    def __init__(self, julia=None):
        from julia import Julia

        self.julia = Julia() if julia is None else julia
        self.magic_re = re.compile(r".*(\s|^)%%?julia\s*")
        # With this regexp, "=%julia Cha<tab>" won't work.  But maybe
        # it's better to be conservative here.

    @property
    def jlcomplete(self):
        from julia.Main._PyJuliaHelper import completions

        return completions

    def julia_completions(self, full_text, offset):
        self.last_text = full_text
        match = self.magic_re.match(full_text)
        if not match:
            return []
        prefix_len = match.end()
        jl_pos = offset - prefix_len
        jl_code = full_text[prefix_len:]
        texts, (jl_start, jl_end), should_complete = self.jlcomplete(jl_code, jl_pos)
        start = jl_start - 1 + prefix_len
        end = jl_end + prefix_len
        completions = [Completion(start, end, txt) for txt in texts]
        self.last_completions = completions
        # if not should_complete:
        #     return []
        return completions


class IPCompleterPatcher(object):
    def __init__(self):
        from julia.Base import VERSION

        if (VERSION.major, VERSION.minor) < (0, 7):
            return

        self.patch_ipcompleter(IPCompleter, JuliaCompleter())

    def patch_ipcompleter(self, IPCompleter, jlcompleter):
        orig__completions = IPCompleter._completions

        def _completions(self, full_text, offset, **kwargs):
            completions = jlcompleter.julia_completions(full_text, offset)
            if completions:
                return completions
            else:
                return orig__completions(self, full_text, offset, **kwargs)

        IPCompleter._completions = _completions

        self.orig__completions = orig__completions
        self.patched__completions = _completions
        self.IPCompleter = IPCompleter


# Make it work with reload:
try:
    PATCHER
except NameError:
    PATCHER = None


def patch_ipcompleter():
    global PATCHER
    if PATCHER is not None:
        return
    PATCHER = IPCompleterPatcher()


# TODO: write `unpatch_ipcompleter`

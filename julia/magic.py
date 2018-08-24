"""
==========================
 Julia magics for IPython
==========================

{JULIAMAGICS_DOC}

Usage
=====

``%%julia``

{JULIA_DOC}
"""

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from __future__ import print_function, absolute_import
import sys

from IPython.core.magic import Magics, magics_class, line_cell_magic
from julia import Julia, JuliaError

#-----------------------------------------------------------------------------
# Main classes
#-----------------------------------------------------------------------------

import IPython.utils.py3compat as compat

@magics_class
class JuliaMagics(Magics):
    """A set of magics useful for interactive work with Julia.
    """
    def __init__(self, shell):
        """
        Parameters
        ----------
        shell : IPython shell

        """

        super(JuliaMagics, self).__init__(shell)
        print("Initializing Julia interpreter. This may take some time...",
              end='')
        # Flush, otherwise the Julia startup will keep stdout buffered
        sys.stdout.flush()
        self._julia = Julia(init_julia=True)
        print()

    @line_cell_magic
    def julia(self, line, cell=None):
        """
        Execute code in Julia, and pull some of the results back into the
        Python namespace.
        """
        src = compat.unicode_type(line if cell is None else cell)

        try:
            ans = self._julia.eval(src)
        except JuliaError as e:
            print(e, file=sys.stderr)
            ans = None

        return ans


class JuliaCompleter(object):

    """
    Simple completion for ``%julia`` line magic.
    """

    @property
    def jlcomplete_texts(self):
        try:
            return self._jlcomplete_texts
        except AttributeError:
            pass

        julia = Julia()
        if julia.eval('VERSION < v"0.7-"'):
            self._jlcomplete_texts = lambda *_: []
            return self._jlcomplete_texts

        self._jlcomplete_texts = julia.eval("""
        import REPL
        (str, pos) -> begin
            ret, _, should_complete =
                REPL.completions(str, pos)
            if should_complete
                return map(REPL.completion_text, ret)
            else
                return []
            end
        end
        """)
        return self._jlcomplete_texts

    def complete_command(self, _ip, event):
        pos = event.text_until_cursor.find("%julia")
        if pos < 0:
            return []
        pos += len("%julia")  # pos: beginning of Julia code
        julia_code = event.line[pos:]
        julia_pos = len(event.text_until_cursor) - pos

        completions = self.jlcomplete_texts(julia_code, julia_pos)
        if "." in event.symbol:
            # When completing (say) "Base.s" we need to add the prefix "Base."
            prefix = event.symbol.rsplit(".", 1)[0]
            completions = [".".join((prefix, c)) for c in completions]
        return completions
    # See:
    # IPython.core.completer.dispatch_custom_completer

    @classmethod
    def register(cls, ip):
        """
        Register `.complete_command` to IPython hook.

        Parameters
        ----------
        ip : IPython.InteractiveShell
            IPython `.InteractiveShell` instance passed to
            `load_ipython_extension`.
        """
        ip.set_hook("complete_command", cls().complete_command,
                    str_key="%julia")
# See:
# https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.hooks.html
# IPython.core.interactiveshell.init_completer
# IPython.core.completerlib (quick_completer etc.)


# Add to the global docstring the class information.
__doc__ = __doc__.format(
    JULIAMAGICS_DOC=' ' * 8 + JuliaMagics.__doc__,
    JULIA_DOC=' ' * 8 + JuliaMagics.julia.__doc__,
)


#-----------------------------------------------------------------------------
# IPython registration entry point.
#-----------------------------------------------------------------------------

def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(JuliaMagics)
    JuliaCompleter.register(ip)

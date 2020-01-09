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

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from __future__ import absolute_import, print_function

import sys
import warnings

from IPython.core.magic import Magics, line_cell_magic, magics_class
from traitlets import Bool, Enum

from .core import Julia, JuliaError
from .tools import redirect_output_streams

try:
    unicode
except NameError:
    unicode = str

try:
    from IPython.core.magic import no_var_expand
except ImportError:

    def no_var_expand(f):
        return f


# ----------------------------------------------------------------------------
# Main classes
# ----------------------------------------------------------------------------


@magics_class
class JuliaMagics(Magics):
    """A set of magics useful for interactive work with Julia.
    """

    highlight = Bool(
        True,
        config=True,
        help="""
        Enable highlighting in `%%julia` magic by monkey-patching
        IPython internal (`TerminalInteractiveShell`).
        """,
    )
    completion = Bool(
        True,
        config=True,
        help="""
        Enable code completion in `%julia` and `%%julia` magics by
        monkey-patching IPython internal (`IPCompleter`).
        """,
    )
    redirect_output_streams = Enum(
        ["auto", True, False],
        "auto",
        config=True,
        help="""
        Connect Julia's stdout and stderr to Python's standard stream.
        "auto" (default) means to do so only in Jupyter.
        """,
    )
    revise = Bool(
        False,
        config=True,
        help="""
        Enable Revise.jl integration.  Revise.jl must be installed
        before using this option (run `using Pkg; Pkg.add("Revise")`).
        """,
    )

    def __init__(self, shell):
        """
        Parameters
        ----------
        shell : IPython shell

        """

        super(JuliaMagics, self).__init__(shell)
        print("Initializing Julia interpreter. This may take some time...", end="")
        # Flush, otherwise the Julia startup will keep stdout buffered
        sys.stdout.flush()
        self._julia = Julia(init_julia=True)
        print()

    @no_var_expand
    @line_cell_magic
    def julia(self, line, cell=None):
        """
        Execute code in Julia, and pull some of the results back into the
        Python namespace.
        """
        src = unicode(line if cell is None else cell)

        # We assume the caller's frame is the first parent frame not in the
        # IPython module. This seems to work with IPython back to ~v5, and
        # is at least somewhat immune to future IPython internals changes,
        # although by no means guaranteed to be perfect.
        caller_frame = sys._getframe(3)
        while caller_frame.f_globals.get("__name__").startswith("IPython"):
            caller_frame = caller_frame.f_back

        return_value = "nothing" if src.strip().endswith(";") else ""

        return self._julia.eval(
            """
            _PyJuliaHelper.@prepare_for_pyjulia_call begin
                begin %s end
                %s
            end
            """
            % (src, return_value)
        )(self.shell.user_ns, caller_frame.f_locals)


# Add to the global docstring the class information.
__doc__ = __doc__.format(
    JULIAMAGICS_DOC=" " * 8 + JuliaMagics.__doc__,
    JULIA_DOC=" " * 8 + JuliaMagics.julia.__doc__,
)


def should_redirect_output_streams():
    try:
        OutStream = sys.modules["ipykernel"].iostream.OutStream
    except (KeyError, AttributeError):
        return False
    return isinstance(sys.stdout, OutStream)


# ----------------------------------------------------------------------------
# IPython registration entry point.
# ----------------------------------------------------------------------------


def load_ipython_extension(ip):
    """Load the extension in IPython."""

    # This is equivalent to `ip.register_magics(JuliaMagics)` (but it
    # let us access the instance of `JuliaMagics`):
    magics = JuliaMagics(shell=ip)
    ip.register_magics(magics)

    template = "Incompatible upstream libraries. Got ImportError: {}"
    if magics.highlight:
        try:
            from .ipy.monkeypatch_interactiveshell import patch_interactiveshell
        except ImportError as err:
            warnings.warn(template.format(err))
        else:
            patch_interactiveshell(ip)

    if magics.completion:
        try:
            from .ipy.monkeypatch_completer import patch_ipcompleter
        except ImportError as err:
            warnings.warn(template.format(err))
        else:
            patch_ipcompleter()

    if magics.redirect_output_streams is True or (
        magics.redirect_output_streams == "auto" and should_redirect_output_streams()
    ):
        redirect_output_streams()

    if magics.revise:
        from .ipy.revise import register_revise_hook

        register_revise_hook(ip)

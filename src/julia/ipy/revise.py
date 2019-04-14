from __future__ import absolute_import, print_function

import warnings

revise_errors_limit = 1


def enable_revise():
    """
    (Re-)enable Revise.jl integration.

    IPython magic must be loaded with ``JuliaMagics.revise = True`` option.
    """
    global revise_errors
    revise_errors = 0


def disable_revise():
    """
    Disable Revise.jl integration.
    """
    global revise_errors
    revise_errors = revise_errors_limit


def make_revise_wrapper(revise):
    def revise_wrapper():
        global revise_errors

        if revise_errors >= revise_errors_limit:
            return

        try:
            revise()
        except Exception as err:
            warnings.warn(str(err))
            revise_errors += 1
            if revise_errors >= revise_errors_limit:
                warnings.warn(
                    "Turning off Revise.jl."
                    "  Run `julia.enable_revise()` to re-enable it."
                )
        else:
            revise_errors = 0

    return revise_wrapper


def register_revise_hook(ip):
    global revise_errors

    try:
        from julia.Revise import revise
    except ImportError:
        warnings.warn(
            "Failed to import Revise.jl."
            '  Install it with `using Pkg; Pkg.add("Revise")` in Julia REPL.'
        )
        return

    revise_errors = 0
    ip.events.register("pre_execute", make_revise_wrapper(revise))

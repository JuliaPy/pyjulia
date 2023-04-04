if VERSION < v"0.7-"
    error("Unsupported Julia version: $VERSION")
end

import PyCall

@debug "Trying to import Python module `julia`..."
try
    PyCall.pyimport("julia")
catch err
    if PyCall.pyisinstance(err.val, PyCall.pybuiltin("ImportError"))
        @error """
Python module `julia` cannot be imported.  It is likely that you are
installing PyJulia in the Python environment that is not used by PyCall.  Note
that `python-jl` program needs PyJulia to be installed in the Python environment
used by PyCall.

PyCall is configured to use Python executable:
    $(PyCall.pyprogramname)

See PyCall documentation:
    https://github.com/JuliaPy/PyCall.jl#specifying-the-python-version
        """
        exit(1)
    end
    rethrow()
end

@debug "Trying to import Python module `julia.pseudo_python_cli`..."
let cli = try
        PyCall.pyimport("julia.pseudo_python_cli")
    catch err
        if PyCall.pyisinstance(err.val, PyCall.pybuiltin("ImportError"))
            @error "Incompatible version of PyJulia is installed for PyCall."
            exit(1)
        end
        rethrow()
    end,
    main = try
        cli.main
    catch
        cli[:main]
    end,
    code = main(ARGS)

    if code isa Integer
        exit(code)
    end
end

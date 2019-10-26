OP, python, libpython = ARGS

# Special exit codes for this script.
# (see: https://www.tldp.org/LDP/abs/html/exitcodes.html)
code_no_precompile_needed = 113


if VERSION < v"0.7.0"
    error("Unsupported Julia version $VERSION")
end

using Pkg
using InteractiveUtils

@info "Julia version info"
versioninfo(verbose=true)

@info "Julia executable: $(Base.julia_cmd().exec[1])"

pkgid = Base.PkgId(Base.UUID(0x438e738f_606a_5dbb_bf0a_cddfbfd45ab0), "PyCall")
pycall_is_installed = Base.locate_package(pkgid) !== nothing

@info "Trying to import PyCall..."

module DummyPyCall
python = nothing
libpython = nothing
end

try
    # `import PyCall` cannot be caught?
    global PyCall = Base.require(Main, :PyCall)
catch err
    @error "`import PyCall` failed" exception=(err, catch_backtrace())
    global PyCall = DummyPyCall
end


ENV["PYTHON"] = python

# TODO: warn if some relevant JULIA_* environment variables are set
# TODO: use PackageSpec to specify PyCall's UUID

print_logfile = true

function build_pycall()
    if VERSION >= v"1.1.0-rc1"
        @info """Run `Pkg.build("PyCall"; verbose=true)`"""
        Pkg.build("PyCall"; verbose=true)
        global print_logfile = false
    else
        @info """Run `Pkg.build("PyCall")`"""
        Pkg.build("PyCall")
    end
end

if OP == "build"
    build_pycall()
elseif PyCall.python == python || PyCall.libpython == libpython
    @info """
    PyCall is already installed and compatible with Python executable.

    PyCall:
        python: $(PyCall.python)
        libpython: $(PyCall.libpython)
    Python:
        python: $python
        libpython: $libpython
    """
    exit(code_no_precompile_needed)
else
    if PyCall.python !== nothing
        if isempty(libpython)
            @warn """
            PyCall is already installed.  However, you may have trouble using
            this Python executable because it is statically linked to libpython.

            For more information, see:
                https://pyjulia.readthedocs.io/en/latest/troubleshooting.html

            Python executable:
                $python
            Julia executable:
                $(Base.julia_cmd().exec[1])
            """
            exit(code_no_precompile_needed)
        else
            @info """
            PyCall is already installed but not compatible with this Python
            executable.  Re-building PyCall...
            """
            build_pycall()
        end
    elseif pycall_is_installed
        @info """
        PyCall is already installed but importing it failed.
        Re-building PyCall may fix the issue...
        """
        build_pycall()
    else
        @info "Installing PyCall..."
        Pkg.add("PyCall")
    end
end

modpath = Base.locate_package(pkgid)
pkgdir = joinpath(dirname(modpath), "..")

if print_logfile
    logfile = joinpath(pkgdir, "deps", "build.log")
    if isfile(logfile)
        @info "Build log in $logfile"
        print(stderr, read(logfile, String))
    end
end

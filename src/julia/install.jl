OP, python, libpython = ARGS

# Special exit codes for this script.
# (see: https://www.tldp.org/LDP/abs/html/exitcodes.html)
code_no_precompile_needed = 113


if VERSION < v"0.7.0"
macro info(x)
    :(info($(esc(x))))
end
macro warn(x)
    :(warn($(esc(x))))
end
stderr = STDERR
else
using Pkg
end  # if


@info "Julia version info"
if VERSION >= v"0.7.0-DEV.3630"
using InteractiveUtils
versioninfo(verbose=true)
else
versioninfo(true)
end  # if

@info "Julia executable: $(Base.julia_cmd().exec[1])"


if VERSION < v"0.7.0"
pycall_is_installed = Pkg.installed("PyCall") !== nothing
else
pycall_is_installed = haskey(Pkg.installed(), "PyCall")
end  # if


@info "Trying to import PyCall..."

module DummyPyCall
python = nothing
libpython = nothing
end

try
    # `import PyCall` cannot be caught?
    if VERSION < v"0.7.0"
    Base.require(:PyCall)
    @assert PyCall.python isa String
    else
    global PyCall = Base.require(Main, :PyCall)
    end  # if
catch err
    @static if VERSION < v"0.7.0"
    @warn """
    `import PyCall` failed with:
    $err
    """
    else
    @error "`import PyCall` failed" exception=(err, catch_backtrace())
    end  # if
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

if VERSION < v"0.7.0"
pkgdir = Pkg.dir("PyCall")
else
pkg = Base.PkgId(Base.UUID(0x438e738f_606a_5dbb_bf0a_cddfbfd45ab0), "PyCall")
modpath = Base.locate_package(pkg)
pkgdir = joinpath(dirname(modpath), "..")
end  # if

if print_logfile
    logfile = joinpath(pkgdir, "deps", "build.log")
    if isfile(logfile)
        @info "Build log in $logfile"
        print(stderr, read(logfile, String))
    end
end

OP, python, libpython = ARGS

# Special exit codes for this script.
# (see: https://www.tldp.org/LDP/abs/html/exitcodes.html)
code_no_precompile_needed = 113


if VERSION < v"0.7.0"
    error("Unsupported Julia version $VERSION")
end

const Pkg =
    Base.require(Base.PkgId(Base.UUID("44cfe95a-1eb2-52ea-b672-e2afdf69b78f"), "Pkg"))
const InteractiveUtils = Base.require(Base.PkgId(
    Base.UUID("b77e0a4c-d291-57a0-90e8-8db25a27a240"),
    "InteractiveUtils",
))

@info "Julia version info"
InteractiveUtils.versioninfo(verbose=true)

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
    global PyCall = Base.require(pkgid)
catch err
    @error "`import PyCall` failed" exception=(err, catch_backtrace())
    global PyCall = DummyPyCall
end


ENV["PYTHON"] = python

# TODO: warn if some relevant JULIA_* environment variables are set
# TODO: use PackageSpec to specify PyCall's UUID

function build_pycall()
    modpath = Base.locate_package(pkgid)
    pkgdir = joinpath(dirname(modpath), "..")

    if VERSION >= v"1.1.0-rc1"
        @info """Run `Pkg.build("PyCall"; verbose=true)`"""
        Pkg.build("PyCall"; verbose=true)
    else
        @info """Run `Pkg.build("PyCall")`"""
        Pkg.build("PyCall")
        logfile = joinpath(pkgdir, "deps", "build.log")
        if isfile(logfile)
            @info "Build log in $logfile"
            print(stderr, read(logfile, String))
        end
    end
    depsfile = joinpath(pkgdir, "deps", "deps.jl")
    if isfile(depsfile)
        @info "`$depsfile`"
        print(stderr, read(depsfile, String))
    else
        @error "Missing `deps.jl` file at: `$depsfile`"
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

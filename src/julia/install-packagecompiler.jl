compiler_env, = ARGS

if VERSION < v"0.7-"
    error("Unsupported Julia version $VERSION")
end

using Pkg

function cat_build_log(pkg)
    modpath = Base.locate_package(pkg)
    if modpath !== nothing
        logfile = joinpath(dirname(modpath), "..", "deps", "build.log")
        if isfile(logfile)
            print(stderr, read(logfile, String))
            return
        end
    end
    @error "build.log for $pkg not found"
end

Pkg.activate(compiler_env)
@info "Installing PackageCompiler..."

Pkg.add([
    PackageSpec(
        name = "PackageCompiler",
        uuid = "9b87118b-4619-50d2-8e1e-99f35a4d4d9d",
        version = "0.6",
    )
])
cat_build_log(Base.PkgId(
    Base.UUID("9b87118b-4619-50d2-8e1e-99f35a4d4d9d"),
    "PackageCompiler"))

@info "Loading PackageCompiler..."
using PackageCompiler

@info "PackageCompiler is successfully installed at $compiler_env"

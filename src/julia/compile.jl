compiler_env, script, output = ARGS

if VERSION < v"0.7-"
    error("Unsupported Julia version $VERSION")
end

const Pkg =
    Base.require(Base.PkgId(Base.UUID("44cfe95a-1eb2-52ea-b672-e2afdf69b78f"), "Pkg"))

Pkg.activate(compiler_env)
@info "Loading PackageCompiler..."
using PackageCompiler

@info "Installing PyCall..."
Pkg.activate(".")
Pkg.add([
    Pkg.PackageSpec(
        name = "PyCall",
        uuid = "438e738f-606a-5dbb-bf0a-cddfbfd45ab0",
    ),
])

@info "Compiling system image..."
create_sysimage(
    [:PyCall],
    sysimage_path = output,
    project = ".",
    precompile_execution_file = script,
)

@info "System image is created at $output"

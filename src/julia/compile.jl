compiler_env, script, output = ARGS

if VERSION < v"0.7-"
    error("Unsupported Julia version $VERSION")
end

using Pkg

Pkg.activate(compiler_env)
@info "Loading PackageCompiler..."
using PackageCompiler

@info "Installing PyCall..."
Pkg.activate(".")
Pkg.add([
    PackageSpec(
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

compiler_env, script, output = ARGS

if VERSION < v"0.7-"
    error("Unsupported Julia version $VERSION")
end

using Pkg

if isempty(compiler_env)
    compiler_env = abspath("compiler_env")
    Pkg.activate(compiler_env)
    Pkg.add([
        PackageSpec(
            name = "PackageCompiler",
            uuid = "9b87118b-4619-50d2-8e1e-99f35a4d4d9d",
            version = "0.6",
        )
    ])
else
    Pkg.activate(compiler_env)
end
@info "Loading PackageCompiler..."
using PackageCompiler

@info "Installing PyCall..."
Pkg.activate(".")
Pkg.add([
    PackageSpec(
        name = "PyCall",
        uuid = "438e738f-606a-5dbb-bf0a-cddfbfd45ab0",
    )
    PackageSpec(
        name = "MacroTools",
        uuid = "1914dd2f-81c6-5fcd-8719-6d5c9610ff09",
    )
])

@info "Compiling system image..."
sysout, _curr_syso = compile_incremental("Project.toml", script)

@info "System image is created at $output"
cp(sysout, output, force=true)

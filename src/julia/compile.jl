script, output = ARGS

if VERSION < v"0.7-"
    error("Unsupported Julia version $VERSION")
end

using Pkg

compilerenv = abspath("compilerenv")
Pkg.activate(compilerenv)
Pkg.add([
    PackageSpec(
        name = "PackageCompiler",
        uuid = "9b87118b-4619-50d2-8e1e-99f35a4d4d9d",
        version = "0.6",
    )
])
using PackageCompiler

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

sysout, _curr_syso = compile_incremental("Project.toml", script)

cp(sysout, output, force=true)

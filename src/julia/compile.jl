script, output = ARGS

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
Pkg.add("MacroTools")
Pkg.add("PyCall")

sysout, _curr_syso = compile_incremental("Project.toml", script)

cp(sysout, output, force=true)

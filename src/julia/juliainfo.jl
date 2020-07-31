println(VERSION)
println(VERSION.major)
println(VERSION.minor)
println(VERSION.patch)

VERSION < v"0.7.0" && exit()

const Libdl =
    Base.require(Base.PkgId(Base.UUID("8f399da3-3557-5675-b5ff-fb832c97cbdb"), "Libdl"))
const Pkg =
    Base.require(Base.PkgId(Base.UUID("44cfe95a-1eb2-52ea-b672-e2afdf69b78f"), "Pkg"))

println(Base.Sys.BINDIR)
println(Libdl.dlpath(string("lib", splitext(Base.julia_exename())[1])))
println(unsafe_string(Base.JLOptions().image_file))

pkg = Base.PkgId(Base.UUID(0x438e738f_606a_5dbb_bf0a_cddfbfd45ab0), "PyCall")
modpath = Base.locate_package(pkg)
if modpath !== nothing
    PyCall_depsfile = joinpath(dirname(modpath),"..","deps","deps.jl")
    if isfile(PyCall_depsfile)
        include(PyCall_depsfile)
        println(pyprogramname)
        println(libpython)
    end
end

JULIA = "julia"
JL_SHARE = $(shell julia -e 'print(joinpath(JULIA_HOME, Base.DATAROOTDIR, ${JULIA}))')
CFLAGS   += $(shell $(JL_SHARE)/julia-config.jl --cflags)
LDFLAGS  += $(shell $(JL_SHARE)/julia-config.jl --ldflags)
LDLIBS   += $(shell $(JL_SHARE)/julia-config.jl --ldlibs)

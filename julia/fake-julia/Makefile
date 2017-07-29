all: julia.exe julia-debug.exe
# CLANG_OPTS = --sysroot=$(HOME)/julia/usr/x86_64-w64-mingw32/sys-root/mingw -target x86_64-w64-mingw32
CLANG_OPTS = --sysroot=$(HOME)/julia/usr/i686-w64-mingw32/sys-root/mingw -target i686-w64-mingw32
julia.exe: julia-win.c
	/C/LLVM/bin/clang $(CLANG_OPTS) -o julia.exe julia-win.c -municode
julia-debug.exe: julia-win.c
	/C/LLVM/bin/clang $(CLANG_OPTS) -DDEBUG_VERSION -o julia-debug.exe julia-win.c -municode
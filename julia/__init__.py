import sys
from .core import Julia

#initialize julia interpreter
julia = Julia()

#monkeypatch julia interpreter into module load path
sys.modules["julia"] = julia

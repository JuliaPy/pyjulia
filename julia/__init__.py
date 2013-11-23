import sys
from .core import Julia
j = Julia()
sys.modules["julia"] = j


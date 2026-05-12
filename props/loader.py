import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "props"))
exec(open(os.path.join(_ROOT, "props", "batch_export.py"), encoding="utf-8").read())

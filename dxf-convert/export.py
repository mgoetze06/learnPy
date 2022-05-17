from ezdxf import recover
from ezdxf.addons.drawing import matplotlib

# Exception handling left out for compactness:
doc, auditor = recover.readfile('a0100.dxf')
if not auditor.has_errors:
    matplotlib.qsave(doc.modelspace(), 'a0100.png')
from .base import Panel
from .video import VideoPanel
from .scatter import ScatterPanel

# pyopengl is optional
try: from .mesh import MeshPanel
except: pass
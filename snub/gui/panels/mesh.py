from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtOpenGL
import pyqtgraph.opengl as gl
import h5py, numpy as np, os
from snub.gui.panels import Panel


class MeshPanel(Panel):
    def __init__(self, config, data_path=None, faces_path=None, timestamps_path=None, **kwargs):
        super().__init__(**kwargs)

        h5_path = os.path.join(config['project_directory'], data_path)
        faces_path = os.path.join(config['project_directory'], faces_path) 
        timestamps_path = os.path.join(config['project_directory'], timestamps_path) 

        self.timestamps = np.load(timestamps_path)
        self.verts_dset = h5py.File(h5_path, 'r')['vertices']
        self.faces = np.load(faces_path).squeeze()
        self.face_colors = np.zeros((self.faces.shape[0], 4))

        self.mesh = gl.GLMeshItem(
            vertexes=self.verts_dset[0],
            faces=self.faces,
            faceColors=self.face_colors,
            drawEdges=True,
            smooth=False
        )
        self.mesh.setGLOptions('additive')
        self.initUI()

    def initUI(self):
        self.w = gl.GLViewWidget()
        self.w.setWindowTitle(self.name)
        self.w.setCameraPosition(distance=200, elevation=20)

        floor_grid = gl.GLGridItem()
        floor_grid.setSize(500, 500)
        floor_grid.setSpacing(5, 5)
        self.w.addItem(floor_grid)
        self.w.addItem(self.mesh)
        layout = QVBoxLayout(self)
        layout.addWidget(self.w)
        layout.setContentsMargins(0,0,0,0)
        super().initUI()

    def event(self, event):
        return True

    def update_current_time(self, t):
        frame = min(self.timestamps.searchsorted(t), len(self.timestamps)-1)
        print(frame)
        verts = self.verts_dset[frame]
        verts = verts - verts.mean(axis=0)
        self.mesh.setMeshData(
            vertexes=verts,
            faces=self.faces,
            faceColors=self.face_colors
        )
        

    def update_selection_mask(self, selection_mask):
        pass



    def __del__(self):
        self.verts_dset.file.close()
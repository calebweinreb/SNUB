from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtOpenGL
import pyqtgraph.opengl as gl
import h5py, numpy as np, os
from snub.gui.panels import Panel
from snub.gui.utils import HeaderMixin


class MeshPanel(Panel, HeaderMixin):
    def __init__(self, config, data_path=None, faces_path=None, timestamps_path=None, **kwargs):
        super().__init__(config, **kwargs)

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
        self.initUI(**kwargs)

    def initUI(self, **kwargs):
        super().initUI(**kwargs)
        self.w = gl.GLViewWidget()
        self.w.setCameraPosition(distance=200, elevation=20)

        floor_grid = gl.GLGridItem()
        floor_grid.setSize(2000, 2000)
        floor_grid.setSpacing(20, 20)
        self.w.addItem(floor_grid)
        self.w.addItem(self.mesh)
        self.layout.addWidget(self.w)


    def event(self, event):
        return True

    def update_current_time(self, t):
        frame = min(self.timestamps.searchsorted(t), len(self.timestamps)-1)
        verts = self.verts_dset[frame]
        self.mesh.setMeshData(
            vertexes=verts,
            faces=self.faces,
            faceColors=self.face_colors
        )
        x, y, _ = verts.mean(axis=0)
        pos = self.w.setCameraPosition(pos=QVector3D(x, y, 0))

    def __del__(self):
        self.verts_dset.file.close()
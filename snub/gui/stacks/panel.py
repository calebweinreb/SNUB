from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np

from snub.gui.stacks import Stack
from snub.gui.panels import MeshPanel, VideoPanel, ScatterPanel

class PanelStack(Stack):
    def __init__(self, config, selected_intervals, **kwargs):
        super().__init__(config, selected_intervals, **kwargs)

        for scatter_props in config['scatters']: # initialize scatter plots
            scatter_panel = ScatterPanel(config, self.selected_intervals, **scatter_props)
            self.widgets.append(scatter_panel)

        for video_props in config['videos']: # initialize videos
            video_frame = VideoPanel(config, **video_props)
            self.widgets.append(video_frame)

        for mesh_props in config['meshes']:
            mesh_vis = MeshPanel(config, **mesh_props)
            self.widgets.append(mesh_vis)

        self.initUI()


    def initUI(self):
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        self.setSizePolicy(sizePolicy)

        hbox = QHBoxLayout(self)
        self.splitter = QSplitter(Qt.Vertical)
        for i,panel in enumerate(self.widgets):
            self.splitter.addWidget(panel)
            self.splitter.setStretchFactor(i, panel.size_ratio)

        hbox.addWidget(self.splitter)
        self.splitter.setSizes([100000*p.size_ratio for p in self.widgets])
        hbox.setContentsMargins(0, 0, 0, 0)


    def update_current_time(self,t):
        for panel in self.widgets:
            panel.update_current_time(t)

    def update_selected_intervals(self):
        for panel in self.widgets: 
            panel.update_selected_intervals()

    def change_layout_mode(self, layout_mode):
        self.splitter.setOrientation({'columns':Qt.Vertical, 'rows':Qt.Horizontal}[layout_mode])
        super().change_layout_mode(layout_mode)
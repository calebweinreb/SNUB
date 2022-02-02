from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np

from snub.gui.utils import time_to_position, position_to_time
from snub.gui.panels import MeshPanel, VideoPanel, ScatterPanel
from snub.gui.tracks import RasterTraceTrack, TrackOverlay, Timeline 


class Stack(QWidget):
    def __init__(self, config, selected_intervals, **kwargs):
        super().__init__()
        self.widgets = []
        self.selected_intervals = selected_intervals

    def change_layout_mode(self, layout_mode):
        for widget in self.widgets: widget.change_layout_mode(layout_mode)
        

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

class TrackStack(Stack):
    new_current_time = pyqtSignal(float)
    selection_change = pyqtSignal(list, list)

    def __init__(self, config, selected_intervals, zoom_gain=0.003, min_range=0.1, **kwargs):
        super().__init__(config, selected_intervals, **kwargs)
        self.bounds = config['bounds']
        self.zoom_gain = zoom_gain
        self.min_range = min_range
        self.current_range = self.bounds
        self.selection_drag_mode = 0 # +1 for shift-click, -1 for command-click
        self.selection_drag_initial_time = None

        self.overlay = TrackOverlay(config, self, selected_intervals)
        self.timeline = Timeline(config)
        self.widgets = [self.timeline]
        for raster_props in config['rasters']:
            track = RasterTraceTrack(config, self.selected_intervals, **raster_props)
            self.widgets.append(track)
        self.timeline.toggle_units_signal.connect(self.overlay.update_time_unit)
        self.initUI()

    def _time_to_position(self, t):
        return time_to_position(self.current_range, self.width(), t)

    def _position_to_time(self, p):
        return position_to_time(self.current_range, self.width(), p)

    def initUI(self):
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        self.setSizePolicy(sizePolicy)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        for i,track in enumerate(self.widgets[1:]):
            self.splitter.addWidget(track)
            self.splitter.setStretchFactor(i, track.height_ratio)

        layout = QVBoxLayout(self)
        layout.addWidget(self.splitter)
        layout.addWidget(self.timeline)
        layout.setContentsMargins(0, 0, 0, 0)
        self.overlay.raise_()

    def wheelEvent(self,event):
        if np.abs(event.angleDelta().y()) > np.abs(event.angleDelta().x()): 
            # vertical motion -> zoom
            event_t = self._position_to_time(event.x())
            scale_change = max(1+event.angleDelta().y()*self.zoom_gain, self.min_range/(self.current_range[1]-self.current_range[0]))
            new_range = [
                max((self.current_range[0]-event_t)*scale_change+event_t,self.bounds[0]),
                min((self.current_range[1]-event_t)*scale_change+event_t,self.bounds[1])]
            self.update_current_range(new_range=new_range)

        if np.abs(event.angleDelta().y()) < np.abs(event.angleDelta().x()): 
            # horizontal motion -> pan
            delta_t = -event.angleDelta().x()/self.width() * (self.current_range[1]-self.current_range[0])
            delta_t = np.clip(delta_t, self.bounds[0]-self.current_range[0],self.bounds[1]-self.current_range[1])
            new_range = [self.current_range[0]+delta_t ,self.current_range[1]+delta_t]
            self.update_current_range(new_range=new_range)

    def mouseMoveEvent(self, event):
        t = max(self._position_to_time(event.x()),0)
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            self.selection_drag_move(t, 1)
        elif modifiers == Qt.ControlModifier:
            self.selection_drag_move(t, -1)
        elif self.selection_drag_mode == 0:
            self.new_current_time.emit(t)        

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            t = max(self._position_to_time(event.x()),0)
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ShiftModifier:
                self.selection_drag_start(t, 1)
            elif modifiers == Qt.ControlModifier:
                self.selection_drag_start(t, -1)
            else:
                self.new_current_time.emit(t)

    def mouseReleaseEvent(self, event):
        self.selection_drag_end()

    def selection_drag_start(self, t, mode):
        self.selection_drag_mode = mode
        self.selection_drag_initial_time = t

    def selection_drag_end(self):
        self.selection_drag_mode = 0
        self.selection_drag_initial_time = None

    def selection_drag_move(self, t, mode):
        if self.selection_drag_mode == mode:
            s,e = sorted([self.selection_drag_initial_time,t])
            self.selection_change.emit([(s,e)], [mode==1])

    def update_current_range(self, new_range=None):
        if new_range is not None: self.current_range = new_range
        for child in self.widgets+[self.overlay]: 
            child.update_current_range(self.current_range)

    def update_current_time(self, t):
        self.overlay.vlines['cursor']['time'] = t
        self.overlay.update()

    def update_selected_intervals(self):
        self.overlay.update_selected_intervals()

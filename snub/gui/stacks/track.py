from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np

from snub.gui.stacks import Stack
from snub.gui.tracks import *

class TrackStack(Stack):
    new_current_time = pyqtSignal(float)
    selection_change = pyqtSignal(list, list)

    def __init__(self, config, selected_intervals):
        super().__init__(config, selected_intervals)
        self.bounds = config['bounds']
        self.center_playhead_policy = config['center_playhead']
        self.zoom_gain = config['zoom_gain']
        self.min_range = config['min_range']
        self.size_ratio = config['tracks_size_ratio']
        self.current_range = self.bounds
        self.selection_drag_mode = 0 # +1 for shift-click, -1 for command-click
        self.selection_drag_initial_time = None

        self.overlay = TrackOverlay(config, self, selected_intervals)
        self.timeline = Timeline(config)
        self.widgets = [self.timeline]

        for props in config['heatmap']:
            if props['add_traceplot']:
                track = HeatmapTraceGroup(config, self.selected_intervals, **props)
            else: track = HeadedHeatmap(config, self.selected_intervals, **props)
            self.widgets.append(track)

        for props in config['spikeplot']:
            if props['add_traceplot']:
                track = SpikePlotTraceGroup(config, self.selected_intervals, **props)
            else: track = HeadedSpikePlot(config, self.selected_intervals, **props)
            self.widgets.append(track)

        for props in config['traceplot']:
            track = HeadedTracePlot(config, **props)
            self.widgets.append(track)

        self.timeline.toggle_units_signal.connect(self.overlay.update_time_unit)
        self.initUI()

    def _time_to_position(self, t):
        p = time_to_position(self.current_range, self.width(), t)
        return p

    def _position_to_time(self, p):
        return position_to_time(self.current_range, self.width(), p)

    def initUI(self):
        super().initUI()

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        for track in self.widgets[1:]: self.splitter.addWidget(track)
        layout = QVBoxLayout(self)
        layout.addWidget(self.splitter)
        layout.addWidget(self.timeline)
        layout.setContentsMargins(0, 0, 0, 0)
        self.splitter.setSizes([w.height_ratio*1000 for w in self.widgets[1:]])
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
        t = np.clip(self._position_to_time(event.x()),*self.bounds)
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            self.selection_drag_move(t, 1)
        elif modifiers == Qt.ControlModifier:
            self.selection_drag_move(t, -1)
        elif self.selection_drag_mode == 0:
            self.new_current_time.emit(t)        

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            t = np.clip(self._position_to_time(event.x()),*self.bounds)
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
        self.overlay.markers['cursor']['time'] = t
        self.overlay.update()

    def update_selected_intervals(self):
        self.overlay.update_selected_intervals()

    def center_at_time(self, t):
        target_shift = t - self._position_to_time(self.width()/2)
        min_shift = self.bounds[0]-self.current_range[0]
        max_shift = self.bounds[1]-self.current_range[1]
        shift = np.clip(target_shift, min_shift, max_shift)
        self.update_current_range(new_range=(self.current_range[0]+shift,self.current_range[1]+shift))

    def tracks_flat(self):
        tracks = []
        for track in self.widgets:
            if isinstance(track, TrackGroup):
                tracks += list(track.tracks.values())
            else: tracks.append(track)
        return tracks



from PyQt5.QtCore import QDir, Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
from functools import partial
import pyqtgraph as pg
import sys
import os
import cv2
import json
import numpy as np
import cmapy
import time
import colorsys



def time_to_position(current_range, width, t):
    pos_rel = (t - current_range[0]) / (current_range[1]-current_range[0])
    return pos_rel * width

def position_to_time(current_range, width, p):
    return p/width * (current_range[1]-current_range[0]) + current_range[0]




class TrackStack(QWidget):
    new_current_time = pyqtSignal(float)
    selection_change = pyqtSignal(list, list)

    def __init__(self, config, selected_intervals, zoom_gain=0.003, min_range=0.1):
        super().__init__()
        self.selected_intervals = selected_intervals
        self.bounds = config['bounds']
        self.zoom_gain = zoom_gain
        self.min_range = min_range
        self.current_range = self.bounds
        self.selection_drag_mode = 0 # +1 for shift-click, -1 for command-click
        self.selection_drag_initial_time = None

        self.overlay = TrackOverlay(config, self, selected_intervals)
        self.timeline = Timeline(config)
        self.tracks = [self.timeline]
        for raster_props in config['rasters']:
            track = RasterTraceGroup(config, self.selected_intervals, **raster_props)
            self.tracks.append(track)
        self.timeline.toggle_units_signal.connect(self.overlay.update_time_unit)
        self.initUI()

    def _time_to_position(self, t):
        return time_to_position(self.current_range, self.width(), t)

    def _position_to_time(self, p):
        return position_to_time(self.current_range, self.width(), p)

    def initUI(self):
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        self.setSizePolicy(sizePolicy)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        for track in self.tracks[1:]:
            self.splitter.addWidget(track)
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
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.selection_drag_move(t, 1)
        elif modifiers == QtCore.Qt.ControlModifier:
            self.selection_drag_move(t, -1)
        elif self.selection_drag_mode == 0:
            self.new_current_time.emit(t)        

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            t = max(self._position_to_time(event.x()),0)
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                self.selection_drag_start(t, 1)
            elif modifiers == QtCore.Qt.ControlModifier:
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
        for child in self.tracks+[self.overlay]: 
            child.update_current_range(self.current_range)

    def update_current_time(self, t):
        self.overlay.vlines['cursor']['time'] = t
        self.overlay.update()

    def update_selected_intervals(self):
        self.overlay.update_selected_intervals()



class Track(QWidget):
    def __init__(self, config, parent=None, height_ratio=1, **kwargs):
        super().__init__(parent=parent)
        self.current_range = config['bounds']
        self.current_time = config['current_time']
        self.timestep = config['timestep']
        self.show_timestep = False
        self.height_ratio = height_ratio

    def _time_to_position(self, t):
        return time_to_position(self.current_range, self.width(), t)

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.update()

    def update_time_unit(self, show_timestep):
        self.show_timestep = show_timestep
        self.update()

    def get_time_label(self, t):
        if self.show_timestep: 
            return repr(int(np.around(t/self.timestep)))
        else: 
            mm = str(int(t/60))
            ss = str(int(t%60))
            return mm.zfill(2)+':'+ss.zfill(2)

    def initUI(self):
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setVerticalStretch(self.height_ratio)
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(1,1)
        self.saved_height = self.height()

    def set_height(self, height):
        self.resize(self.width(), height)
        splitter = self.parent()
        sizes = splitter.sizes()
        sizes[splitter.indexOf(self)] = height
        splitter.setSizes(sizes)




class Timeline(Track):
    toggle_units_signal = QtCore.pyqtSignal(bool)

    def __init__(self, config):
        super().__init__(config)
        self.TIMESTEP_SPACING_OPTIONS = config['timestep'] * np.array([1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 1000000])
        self.SECOND_SPACING_OPTIONS = np.array([1, 5, 10, 30, 60, 120, 300, 600, 900, 1800, 3600])
        self.MAX_TICKS_VISIBLE = 20
        self.HEIGHT = 45
        self.TICK_HEIGHT = 10
        self.TICK_LABEL_WIDTH = 100
        self.TICK_LABEL_MARGIN = 2
        self.TICK_LABEL_HEIGHT = 50

        self.timesteps_button = QRadioButton('timesteps')
        self.minutes_seconds_button = QRadioButton('mm:ss')
        self.minutes_seconds_button.setChecked(True)
        self.timesteps_button.toggled.connect(self.toggle_unit)
        self.minutes_seconds_button.toggled.connect(self.toggle_unit)
        self.initUI()

    def initUI(self):
        self.resize(self.width(),self.HEIGHT)
        # Set Background
        pal = QPalette()
        pal.setColor(QPalette.Background, QColor(20,20,20))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.setFixedHeight(self.HEIGHT)

        radio_button_stylesheet = """
            QRadioButton {
                font: 12pt Helvetica;
                color: rgb(150,150,150);
            }
            QRadioButton::indicator {
                width: 7px;
                height: 7px;
            }
            QRadioButton::indicator:checked {
                background-color: rgb(100,100,100);
                border: 1px solid rgb(150,150,150);
            }
            QRadioButton::indicator:unchecked {
                background-color: rgb(20,20,20);
                border: 1px solid rgb(150,150,150);
            }
        """
        self.timesteps_button.setStyleSheet(radio_button_stylesheet)
        self.minutes_seconds_button.setStyleSheet(radio_button_stylesheet)
        button_strip = QHBoxLayout()
        button_strip.addStretch(0)
        button_strip.addWidget(self.timesteps_button)
        button_strip.addWidget(self.minutes_seconds_button)
        button_strip.addStretch(0)
        button_strip.setSpacing(10)
        button_strip.setContentsMargins(5,0,5,0)
        vbox = QVBoxLayout(self)
        vbox.addStretch(0)
        vbox.addLayout(button_strip)
        vbox.setContentsMargins(0,0,0,5)

    def toggle_unit(self):
        if self.minutes_seconds_button.isChecked(): self.show_timestep = False
        if self.timesteps_button.isChecked(): self.show_timestep = True
        self.toggle_units_signal.emit(self.show_timestep)
        self.update()

    def get_visible_tick_positions(self):
        if self.show_timestep: spacing_options = self.TIMESTEP_SPACING_OPTIONS
        else: spacing_options = self.SECOND_SPACING_OPTIONS
        visible_range = self.current_range[1]-self.current_range[0]
        best_spacing = np.min(np.nonzero(visible_range/spacing_options < self.MAX_TICKS_VISIBLE)[0])
        tick_interval = spacing_options[best_spacing]
        first_tick = self.current_range[0] - self.current_range[0]%tick_interval + tick_interval
        tick_times = np.arange(first_tick,self.current_range[1],tick_interval)
        tick_positions = self._time_to_position(tick_times)
        return tick_times,tick_positions

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.setPen(QColor(150, 150, 150))
        qp.setFont(QFont("Helvetica [Cronyx]", 10))
        qp.setRenderHint(QPainter.Antialiasing)
        tick_times,tick_positions = self.get_visible_tick_positions()
        for t,p in zip(tick_times,tick_positions): 
            label = self.get_time_label(t)
            qp.drawLine(p,0,p,self.TICK_HEIGHT)
            qp.drawText(
                p-self.TICK_LABEL_WIDTH//2,
                self.TICK_HEIGHT+self.TICK_LABEL_MARGIN,
                self.TICK_LABEL_WIDTH,
                self.TICK_LABEL_HEIGHT,
                Qt.AlignHCenter, label)
        qp.end()




class TrackOverlay(Track):
    def __init__(self, config, parent, selected_intervals):
        super().__init__(config, parent=parent)
        self.selected_intervals = selected_intervals
        self.vlines = config['vlines']
        self.vlines['cursor'] = {'time':self.current_time, 'color':(250,250,250), 'linewidth':1}
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.CURSOR_LABEL_LEFT_MARGIN = 5
        self.CURSOR_LABEL_BOTTOM_MARGIN = 5
        self.CURSOR_LABEL_HEIGHT = 15
        self.CURSOR_LABEL_WIDTH = 100

    def update_selected_intervals(self):
        self.update()

    def paintEvent(self, event):
        self.resize(self.parent().size())
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        for key,vline in self.vlines.items():
            qp.setPen(QPen(QColor(*vline['color']),vline['linewidth']))
            r = self._time_to_position(vline['time'])
            if r > 0 and r < self.width():
                qp.drawLine(r,0,r,self.parent().height())
                if key=='cursor' and r < self.width():
                    qp.setFont(QFont("Helvetica [Cronyx]", 12))
                    label = self.get_time_label(vline['time'])
                    qp.drawText(
                        r+self.CURSOR_LABEL_LEFT_MARGIN,
                        self.height()-self.CURSOR_LABEL_HEIGHT, 
                        self.CURSOR_LABEL_WIDTH,
                        self.height()-self.CURSOR_LABEL_BOTTOM_MARGIN,
                        Qt.AlignLeft, label)

        qp.setPen(Qt.NoPen)
        qp.setBrush(QBrush(QColor(255,255,255,100), Qt.SolidPattern))
        for s,e in self.selected_intervals.intervals:
            s_pos = self._time_to_position(s)
            e_pos = self._time_to_position(e)
            if e_pos > 0 and s_pos < self.width(): 
                qp.drawRect(s_pos, 0, e_pos-s_pos, self.height())
        qp.end()





class CheckableComboBox(QtWidgets.QComboBox):
    toggleSignal = QtCore.pyqtSignal(bool, int)
    def __init__(self, width=100):
        super().__init__()
        self.setFixedWidth(width)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def addItem(self, label, color, checked=False):
        super().addItem(label)
        item_index = self.count()-1
        item = self.model().item(item_index,0)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.setForeground(QtGui.QColor('black'))
        item.setBackground(QtGui.QColor(*color))
        if checked: item.setCheckState(QtCore.Qt.Checked)
        else: item.setCheckState(QtCore.Qt.Unchecked)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        checked = item.checkState()==QtCore.Qt.Checked
        self.toggleSignal.emit(not checked, index.row())

    def set_checked(self, index, checked):
        checkState = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
        self.model().item(index,0).setCheckState(checkState)


class TrackGroup(Track):
    def __init__(self, config, name='', tracks={}, track_order=None,
                 header_height=20, initial_visibility={}, **kwargs):
        super().__init__(config)
        assert len(tracks)>0
        self.name = name
        self.tracks = tracks
        self.saved_height = None
        self.track_visibility = dict(initial_visibility)
        if track_order is None: track_order = sorted(tracks.keys())
        self.track_order = track_order
        self.header_height = header_height
        self.toggle_buttons = {}
        for key,track in self.tracks.items():
            toggle_button = QPushButton()
            toggle_button.clicked.connect(partial(self.toggle_visiblity,key,None))
            if not key in initial_visibility: self.track_visibility[key] = True
            self.toggle_buttons[key] = toggle_button
        self.height_ratio = np.sum([track.height_ratio for track in self.tracks.values()])
        self.initUI()

    def initUI(self):
        title = QLabel(self.name)
        header = QWidget(objectName="trackGroup_header")
        header.setFixedHeight(self.header_height)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addStretch(0)
        title_layout.addWidget(title)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(25)
        button_layout.setContentsMargins(0, 0, 0, 0)
        for key in self.track_order: button_layout.addWidget(self.toggle_buttons[key])
        button_layout.addStretch(0)
        header_layout.addLayout(title_layout)
        header_layout.addLayout(button_layout)
        header_layout.setSpacing(25)
        splitter = QSplitter(Qt.Vertical, objectName="trackGroup_splitter")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(splitter)

        for key in self.track_order:
            splitter.addWidget(self.tracks[key])
            if self.track_visibility[key]:
                self.toggle_buttons[key].setText('Hide {}'.format(key))
            else:
                self.tracks[key].hide()
                self.toggle_buttons[key].setText('Show {}'.format(key))

        splitter.setStyleSheet("QSplitter#trackGroup_splitter { background-color: rgb(30,30,30); }")
        self.setStyleSheet("QWidget#trackGroup_header { background-color: rgb(30,30,30); }")
        header.setStyleSheet("QPushButton { color: rgb(150,150,150); border: 0px;}")
        super().initUI()
        
    def update_current_range(self, current_range):
        for track in self.tracks.values():
            track.update_current_range(current_range)

    def toggle_visiblity(self, key, set_visible=None):
        if set_visible is None: 
            set_visible = not self.track_visibility[key]
        if not set_visible:
            self.saved_height = self.height()
            self.tracks[key].hide()
            self.toggle_buttons[key].setText("Show {}".format(key))
            self.track_visibility[key] = False
            if not any(self.track_visibility.values()): 
                self.setFixedHeight(self.header_height)
        else:
            self.tracks[key].show()
            self.toggle_buttons[key].setText("Hide {}".format(key))
            self.track_visibility[key] = True 
            self.setMaximumSize(10000,10000)
            self.setMinimumSize(0,0)
            self.set_height(max(self.saved_height,100))

class RasterTraceGroup(TrackGroup):
    def __init__(self, config, selected_intervals, trace_height_ratio=1, raster_height_ratio=2, **kwargs):
        self.height_ratio = trace_height_ratio + raster_height_ratio
        trace = Trace(config, height_ratio=trace_height_ratio, **kwargs)
        raster = Raster(config, selected_intervals, height_ratio=raster_height_ratio, **kwargs)
        height_ratio = trace_height_ratio+raster_height_ratio
        super().__init__(config, tracks={'trace':trace, 'raster':raster}, 
                    track_order=['trace','raster'], height_ratio=height_ratio, **kwargs)
        raster.display_trace_signal.connect(trace.show_trace)
        raster.display_trace_signal.connect(partial(self.toggle_visiblity,'trace',True))
        
        



class Trace(Track):
    def __init__(self, config, data_path=None, binsize=None, labels=None, start_time=0,
                 initial_visible_traces=[0], controls_padding_right=10, colors=None,
                 yaxis_width=30, controls_padding_top=5, trace_label_margin=4, **kwargs):

        super().__init__(config, **kwargs)
        self.binsize = binsize
        self.start_time = start_time 
        self.controls_padding_right = controls_padding_right
        self.controls_padding_top = controls_padding_top
        self.trace_label_margin = trace_label_margin

        self.data = np.load(os.path.join(config['project_directory'],data_path))
        self.visible_traces = set(initial_visible_traces)

        if labels is not None: assert len(labels)==self.data.shape[0]
        else: labels = [str(i) for i in range(self.data.shape[0])]
        self.labels = labels

        if colors is not None: assert len(colors)==self.data.shape[0]
        else: colors = [self.get_random_color() for i in range(self.data.shape[0])]
        self.colors = colors
        
        self.clearButton = QPushButton("Clear")
        self.clearButton.clicked.connect(self.clear)
        self.dropDown = CheckableComboBox()
        self.dropDown.toggleSignal.connect(self.toggle_trace)

        self.plotWidget = pg.plot()
        self.plotWidget.hideAxis('bottom')
        self.plotWidget.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.plotWidget.showGrid(x=False, y=True, alpha = 0.5)  
        self.plotWidget.getAxis('left').setWidth(yaxis_width)

        self.trace_labels = []
        for i in range(self.data.shape[0]):
            self.dropDown.addItem(self.labels[i], self.colors[i], checked=(i in self.visible_traces))
            trace_label = QPushButton(self.labels[i])
            trace_label.setFixedWidth(trace_label.fontMetrics().boundingRect(trace_label.text()).width()+20)
            trace_label.setStyleSheet("background-color: rgb(20,20,20); color: rgb({},{},{});".format(*self.colors[i]))
            trace_label.pressed.connect(self.trace_label_button_push)
            #trace_label.setMargin(self.trace_label_margin)
            if not i in self.visible_traces: trace_label.hide()
            self.trace_labels.append(trace_label)
    
        self.initUI()
        self.update_plot()
        

    def trace_label_button_push(self):
        index = self.trace_labels.index(self.sender())
        self.hide_trace(index)

    def get_random_color(self):
        hue = np.random.uniform(0,1)
        saturation,value = 1,1
        return [int(255*x) for x in colorsys.hsv_to_rgb(hue,1, 1)]

    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.plotWidget)
        self.controls = QWidget(self)
        control_layout = QHBoxLayout(self.controls)
        control_layout.addStretch(0)
        for trace_label in self.trace_labels: control_layout.addWidget(trace_label, alignment=QtCore.Qt.AlignTop)
        control_layout.addWidget(self.dropDown, alignment=QtCore.Qt.AlignTop)
        control_layout.addWidget(self.clearButton, alignment=QtCore.Qt.AlignTop)
        self.update_controls_geometry()
        super().initUI()

    def clear(self):
        for i in list(self.visible_traces):
            self.hide_trace(i, update_plot=False)
        self.update_plot()

    def toggle_trace(self, state, i):
        if state: self.show_trace(i)
        else: self.hide_trace(i)

    def show_trace(self, index, update_plot=True):
        if not index in self.visible_traces:
            self.dropDown.set_checked(index, True)
            self.visible_traces.add(index)
            self.trace_labels[index].show()
            if update_plot: self.update_plot()

    def hide_trace(self, index, update_plot=True):
        if index in self.visible_traces:
            self.dropDown.set_checked(index, False)
            self.visible_traces.remove(index)
            self.trace_labels[index].hide()
            if update_plot: self.update_plot()

    def update_plot(self):
        self.plotWidget.clear()
        for i in self.visible_traces:
            x = np.arange(self.data.shape[1])*self.binsize+self.start_time
            self.plotWidget.plot(x, self.data[i,:], pen=pg.mkPen(QColor(*self.colors[i])))

    def update_controls_geometry(self): 
        self.controls.setGeometry(0, 0, self.width(), self.height())

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.update_Xrange()

    def update_Xrange(self):
        view_box_width = self.plotWidget.viewGeometry().width()
        yaxis_width = (self.width()-view_box_width)/self.width()*(self.current_range[1]-self.current_range[0])
        self.plotWidget.setXRange(self.current_range[0]+yaxis_width, self.current_range[1], padding=0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_Xrange()
        self.update_controls_geometry()





class AdjustColormapDialog(QDialog):
    def __init__(self, parent, vmin, vmax):
        super().__init__(parent)
        self.parent = parent
        self.vmin = QLineEdit(self,)
        self.vmax = QLineEdit(self)
        self.vmin.setText(str(vmin))
        self.vmax.setText(str(vmax))
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self);
        self.buttonBox.accepted.connect(self.update_colormap_range)
        self.buttonBox.rejected.connect(lambda: self.hide())

        layout = QFormLayout(self)
        layout.addRow("Colormap min", self.vmin)
        layout.addRow("Colormap max", self.vmax)
        layout.addWidget(self.buttonBox)

    def update_colormap_range(self):
        self.parent.update_colormap_range(self.vmin.text(), self.vmax.text())
        self.hide()



class Raster(Track):
    display_trace_signal = QtCore.pyqtSignal(int)
    def __init__(self, config, selected_intervals, data_path=None, binsize=None, start_time=0, 
                 colormap='viridis', downsample_options=np.array([1,3,10,30,100,300,1000]), 
                 max_display_resolution=2000, labels=[], label_margin=10, max_label_width=300, 
                 max_label_height=20, label_color=(255,255,255), label_font_size=12, vmin=0, vmax=1,
                 title_color=(255,255,255), title_margin=5, title_font_size=14, title_height=30, 
                 **kwargs):
        super().__init__(config, **kwargs)
        self.selected_intervals = selected_intervals
        self.binsize = binsize
        self.start_time = start_time
        self.vmin,self.vmax = vmin,vmax
        self.colormap = colormap
        self.labels = labels
        self.downsample_options = downsample_options
        self.max_display_resolution = max_display_resolution
        self.label_margin = 10
        self.max_label_width = max_label_width
        self.max_label_height = max_label_height
        self.label_color = label_color
        self.label_font_size = label_font_size
        self.title_color = title_color
        self.title_margin = title_margin
        self.title_font_size = title_font_size
        self.title_height = title_height
        self.image_data = None

        self.data = np.load(os.path.join(config['project_directory'],data_path))
        self.row_order = np.arange(self.data.shape[0])
        self.adjust_colormap_dialog = AdjustColormapDialog(self, self.vmin, self.vmax)
        self.update_image_data()
        self.initUI()


    def contextMenuEvent(self, event):
        menu_options = [('Adjust colormap range', self.show_adjust_colormap_dialog),
                        ('Reorder by selection', self.reorder_by_selection),
                        ('Restore original order', self.restore_original_order)]

        trace_index = self.row_order[int(event.y()/self.height()*self.data.shape[0])]
        display_trace_slot = lambda: self.display_trace_signal.emit(trace_index)
        menu_options.insert(0,('Dislay trace {}'.format(trace_index), display_trace_slot))

        contextMenu = QMenu(self)
        for name,slot in menu_options:
            label = QLabel(name)
            label.setStyleSheet("""
                QLabel { background-color : #3E3E3E; padding: 10px 12px 10px 12px;}
                QLabel:hover { background-color: #999999;} """)
            action = QWidgetAction(self)
            action.setDefaultWidget(label)
            action.triggered.connect(slot)
            contextMenu.addAction(action)
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

    def reorder_by_selection(self):
        query_intervals = np.stack([
            np.arange(self.data.shape[1])*self.binsize+self.start_time,
            np.arange(1,self.data.shape[1]+1)*self.binsize+self.start_time], axis=1)
        weights = self.selected_intervals.intersection_proportions(query_intervals)
        activation = (self.data * weights).sum(1)
        self.update_row_order(np.argsort(activation)[::-1])

    def restore_original_order(self):
        self.update_row_order(np.arange(self.data.shape[0]))

    def update_row_order(self, order):
        self.row_order = order
        self.update_image_data()
 
    def update_image_data(self):
        data_scaled = np.clip((self.data[self.row_order]-self.vmin)/(self.vmax-self.vmin),0,1)*255
        image_data = cv2.applyColorMap(data_scaled.astype(np.uint8), cmapy.cmap(self.colormap))[:,:,::-1]
        self.image_data = [image_data[:,::d] for d in self.downsample_options]
        self.update()

    def cvImage_to_Qimage(self, cvImage):
        height, width, channel = cvImage.shape
        bytesPerLine = 3 * width
        img_data = np.require(cvImage, np.uint8, 'C')
        return QImage(img_data, width, height, bytesPerLine, QImage.Format_RGB888)

    def get_current_pixmap(self):
        ### NOTE: CAN BE ABSTRACTED: SEE SIMILAR TIMELINE METHOD
        visible_bins = (self.current_range[1]-self.current_range[0])/self.binsize
        downsample_ix = np.min(np.nonzero(visible_bins / self.downsample_options < self.max_display_resolution)[0])
        use_image_data = self.image_data[downsample_ix]
        use_range = [int(np.floor((self.current_range[0]-self.start_time)/self.binsize/self.downsample_options[downsample_ix])),
                     int(np.ceil((self.current_range[1]-self.start_time)/self.binsize/self.downsample_options[downsample_ix]))]
        
        if use_range[0] > use_image_data.shape[1] or use_range[1] < 0: 
            use_image_data = np.zeros((50,50,3))
        elif use_range[0] >= 0 and use_range[1] <= use_image_data.shape[1]:
            use_image_data = use_image_data[:,use_range[0]:use_range[1]]
        elif use_range[0] >= 0 and use_range[1] > use_image_data.shape[1]:
            use_image_data = np.pad(use_image_data[:,use_range[0]:],((0,0),(0,use_range[1]-use_image_data.shape[1]),(0,0)))
        elif use_range[0] < 0 and use_range[1] <= use_image_data.shape[1]:
            use_image_data = np.pad(use_image_data[:,:use_range[1]],((0,0),(-use_range[0],0),(0,0)))
        return  QPixmap(self.cvImage_to_Qimage(use_image_data))


    def update_colormap_range(self, vmin, vmax):
        try:
            vmin,vmax = float(vmin),float(vmax)
            if vmin < vmax:
                self.vmin,self.vmax = vmin,vmax
                self.update_image_data()
        except:
            pass

    def show_adjust_colormap_dialog(self):
        self.adjust_colormap_dialog.show()

    def paintEvent(self, event):
        qp = QPainter(self)
        pixmap = self.get_current_pixmap().scaled(self.size()) #, transformMode=QtCore.Qt.SmoothTransformation)

        qp.setRenderHint(QPainter.Antialiasing)
        qp.drawPixmap(QtCore.QPoint(0,0), pixmap)
        qp.setPen(QColor(*self.label_color))
        qp.setFont(QFont("Helvetica [Cronyx]", self.label_font_size))
        for i,label in enumerate(self.labels):
            height = (self.row_order==i).nonzero()[0][0]
            center_height = (height+.5)/self.data.shape[0]*self.height()
            qp.drawText(self.label_margin, center_height-self.max_label_height//2, 
                self.max_label_width, self.max_label_height, Qt.AlignVCenter, label)




from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
import os
from functools import partial
from snub.gui.utils import HeaderMixin



def time_to_position(current_range, width, t):
    pos_rel = (t - current_range[0]) / (current_range[1]-current_range[0])
    return pos_rel * width

def position_to_time(current_range, width, p):
    return p/width * (current_range[1]-current_range[0]) + current_range[0]



class Track(QWidget):
    def __init__(self, config, parent=None, height_ratio=1, order=0, **kwargs):
        super().__init__(parent=parent)
        self.layout_mode = config['layout_mode']
        self.current_range = config['bounds']
        self.current_time = config['init_current_time']
        self.layout_mode = config['layout_mode']
        self.min_step = config['min_step']
        self.show_min_step = False
        self.show_subsecond = False
        self.height_ratio = height_ratio
        self.order = order


    def _time_to_position(self, t):
        return time_to_position(self.current_range, self.width(), t)

    def update_current_range(self, current_range):
        self.current_range = current_range
        if current_range[1]-current_range[0] < 10: self.show_subsecond = True
        else: self.show_subsecond = False
        self.update()

    def update_time_unit(self, show_min_step):
        self.show_min_step = show_min_step
        self.update()

    def get_time_label(self, t):
        if self.show_min_step: 
            return repr(int(np.around(t/self.min_step)))
        else: 
            mm = str(int(t/60))
            if self.show_subsecond:
                ss = str(round(t%60,3))
            else:
                ss = str(int(t%60))
            return mm.zfill(2)+':'+ss.zfill(2)

    def change_layout_mode(self, layout_mode):
        self.layout_mode = layout_mode
        if isinstance(self, HeaderMixin):
            self.save_current_size()
            self.update_layout()


class Timeline(Track):
    toggle_units_signal = pyqtSignal(bool)
    TIMESTEP_SPACING_OPTIONS = np.array([1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 1000000])
    SECOND_SPACING_OPTIONS = np.array([0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10, 30, 60, 120, 300, 600, 900, 1800, 3600])
    MAX_TICKS_VISIBLE = 20
    HEIGHT = 45
    TICK_HEIGHT = 10
    TICK_LABEL_WIDTH = 100
    TICK_LABEL_MARGIN = 2
    TICK_LABEL_HEIGHT = 50

    def __init__(self, config):
        super().__init__(config)
        self.timestep_spacing_options = config['min_step'] * self.TIMESTEP_SPACING_OPTIONS
        self.min_steps_button = QRadioButton('timesteps')
        self.minutes_seconds_button = QRadioButton('mm:ss')
        self.minutes_seconds_button.setChecked(True)
        self.min_steps_button.toggled.connect(self.toggle_unit)
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
        self.min_steps_button.setStyleSheet(radio_button_stylesheet)
        self.minutes_seconds_button.setStyleSheet(radio_button_stylesheet)
        button_strip = QHBoxLayout()
        button_strip.addStretch(0)
        button_strip.addWidget(self.min_steps_button)
        button_strip.addWidget(self.minutes_seconds_button)
        button_strip.addStretch(0)
        button_strip.setSpacing(10)
        button_strip.setContentsMargins(5,0,5,0)
        vbox = QVBoxLayout(self)
        vbox.addStretch(0)
        vbox.addLayout(button_strip)
        vbox.setContentsMargins(0,0,0,5)

    def toggle_unit(self):
        if self.minutes_seconds_button.isChecked(): self.show_min_step = False
        if self.min_steps_button.isChecked(): self.show_min_step = True
        self.toggle_units_signal.emit(self.show_min_step)
        self.update()

    def get_visible_tick_positions(self):
        if self.show_min_step: spacing_options = self.timestep_spacing_options
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
        self.markers = config['markers']
        self.markers['cursor'] = {'time':self.current_time, 'color':(250,250,250)}
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
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
        for key,marker in self.markers.items():
            qp.setPen(QPen(QColor(*marker['color']),1))
            r = self._time_to_position(marker['time'])
            if r > 0 and r < self.width():
                qp.drawLine(r,0,r,self.parent().height())
                if key=='cursor' and r < self.width():
                    qp.setFont(QFont("Helvetica [Cronyx]", 12))
                    label = self.get_time_label(marker['time'])
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




class TrackGroup(Track, HeaderMixin):
    def __init__(self, config, tracks={}, track_order=None, **kwargs):
        super().__init__(config, **kwargs)
        assert len(tracks)>0
        self.tracks = tracks
        if track_order is None: self.track_order = sorted(tracks.keys())
        else: self.track_order = track_order
        self.initUI(**kwargs)
        
    def initUI(self, **kwargs):
        super().initUI(**kwargs)
        self.splitter = QSplitter(Qt.Vertical, objectName="trackGroup_splitter")
        for key in self.track_order: self.splitter.addWidget(self.tracks[key])
        self.splitter.setSizes([self.tracks[key].height_ratio for key in self.track_order])
        self.splitter.setStyleSheet("QSplitter#trackGroup_splitter { background-color: rgb(30,30,30); }")
        self.layout.addWidget(self.splitter)

    def update_current_range(self, current_range):
        for track in self.tracks.values():
            track.update_current_range(current_range)



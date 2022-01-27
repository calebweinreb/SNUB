from PyQt5.QtCore import QDir, Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
import pyqtgraph as pg
import sys
import os
import cv2
import json
import numpy as np
import cmapy
import time
import colorsys

def get_minutes_seconds(position, fps=30):
    mm = str(int(position/60/fps))
    ss = str(int(position/fps)%60)
    return mm.zfill(2)+':'+ss.zfill(2)


class CheckableComboBox(QtWidgets.QComboBox):
    toggleSignal = QtCore.pyqtSignal(bool, int)
    def __init__(self, width=100):
        super().__init__()
        self.setFixedWidth(width)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def addItem(self, label, color, checked=False):
        super(CheckableComboBox, self).addItem(label)
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


class Trace(QWidget):
    def __init__(self, trackStack, data_path=None, project_directory=None, height_ratio=1, 
                 labels=None, colors=None, initial_visible_traces=set([0]), 
                 controls_padding_right=10, controls_padding_top=5, trace_label_margin=4,
                 **kwargs):

        super().__init__()
        self.trackStack = trackStack
        self.current_range = trackStack.current_range
        self.height_ratio = height_ratio
        self.controls_padding_right = controls_padding_right
        self.controls_padding_top = controls_padding_top
        self.trace_label_margin = trace_label_margin

        assert data_path is not None and project_directory is not None
        self.data = np.load(os.path.join(project_directory,data_path))
        self.visible_traces = initial_visible_traces

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
        
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setVerticalStretch(self.height_ratio)
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(1,1)
        self.update()

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
            x,y,color = range(self.data.shape[1]), self.data[i,:], self.colors[i]
            self.plotWidget.plot(x, y, pen=pg.mkPen(QColor(*color)))

    def update_controls_geometry(self): 
        self.controls.setGeometry(0, 0, self.width(), self.height())

    def resizeEvent(self, event): #2
        super().resizeEvent(event)
        self.update_controls_geometry()

    def update_current_range(self, current_range):
        view_box_width = self.plotWidget.viewGeometry().width()
        relative_yaxis_width = (self.width()-view_box_width)/self.width()
        xmin = current_range[0] + relative_yaxis_width*(current_range[1]-current_range[0])
        self.plotWidget.setXRange(xmin, current_range[1], padding=0)

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


class Raster(QWidget):
    display_trace_signal = QtCore.pyqtSignal(int)
    def __init__(self, trackStack, data_path=None, project_directory=None, height_ratio=1,
                 name="", vmin=0, vmax=1, colormap='viridis', downsample_options=np.array([1,10,100]), 
                 max_display_resolution=2000, labels=[], label_margin=10, max_label_width=300, 
                 max_label_height=20, label_color=(255,255,255), label_font_size=12,
                 title_color=(255,255,255), title_margin=5, title_font_size=14, title_height=30, 
                 **kwargs):
        super().__init__()
        self.trackStack = trackStack
        self.current_range = trackStack.current_range
        self.bounds = trackStack.bounds
        self.vmin,self.vmax = vmin,vmax
        self.colormap = colormap
        self.labels = labels
        self.name = name
        self.height_ratio = height_ratio
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
        self.has_trace_track = False

        assert data_path is not None and project_directory is not None
        self.data = np.load(os.path.join(project_directory,data_path))
        self.row_order = np.arange(self.data.shape[0])
        self.adjust_colormap_dialog = AdjustColormapDialog(self, self.vmin, self.vmax)
        self.update_image_data()
        self.initUI()


    def contextMenuEvent(self, event):
        menu_options = [('Adjust colormap range', self.show_adjust_colormap_dialog),
                        ('Reorder by selection', self.reorder_by_selection),
                        ('Restore original order', self.restore_original_order)]

        if self.has_trace_track:
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
        mask = self.trackStack.selection_mask>0
        activation = self.data[:,self.bounds[0]:self.bounds[1]][:,mask].mean(1)
        self.update_row_order(np.argsort(activation)[::-1])

    def restore_original_order(self):
        self.update_row_order(np.arange(self.data.shape[0]))

    def update_row_order(self, order):
        self.row_order = order
        self.update_image_data()
 
    def update_image_data(self):
        data_scaled = np.clip((self.data[self.row_order]-self.vmin)/(self.vmax-self.vmin),0,1)*255
        self.image_data = cv2.applyColorMap(data_scaled.astype(np.uint8), cmapy.cmap(self.colormap))[:,:,::-1]
        self.update()

    def initUI(self):
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setVerticalStretch(self.height_ratio)
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(1,1)
        self.update()

    def cvImage_to_Qimage(self, cvImage):
        height, width, channel = cvImage.shape
        bytesPerLine = 3 * width
        img_data = np.require(cvImage, np.uint8, 'C')
        return QImage(img_data, width, height, bytesPerLine, QImage.Format_RGB888)

    def get_current_pixmap(self):
        ### NOTE: CAN BE ABSTRACTED: SEE SIMILAR TIMELINE METHOD
        current_range = self.current_range
        visible_range = self.current_range[1]-self.current_range[0]
        best_downsample = np.min(np.nonzero(visible_range / self.downsample_options < self.max_display_resolution)[0])
        downsample = self.downsample_options[best_downsample]
        cropped_image = self.image_data[:,self.current_range[0]:self.current_range[1]][:,::downsample]
        return  QPixmap(self.cvImage_to_Qimage(cropped_image))

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.update()

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
        for i,label in self.labels:
            height = (self.row_order==i).nonzero()[0][0]
            center_height = (height+.5)/self.data.shape[0]*self.height()
            qp.drawText(self.label_margin, center_height-self.max_label_height//2, 
                self.max_label_width, self.max_label_height, Qt.AlignVCenter, label)



class Timeline(QWidget):
    toggle_units_signal = QtCore.pyqtSignal(bool)

    def __init__(self, trackStack, fps):
        super().__init__()
        self.fps = fps
        self.current_range = trackStack.current_range
        self.FRAME_SPACING_OPTIONS = np.array([1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000])
        self.SECOND_SPACING_OPTIONS = np.array([1, 5, 10, 30, 60, 120, 300, 600, 900, 1800, 3600])*fps
        self.MAX_TICKS_VISIBLE = 20
        self.HEIGHT = 50
        self.TICK_HEIGHT = 10
        self.TICK_LABEL_WIDTH = 100
        self.TICK_LABEL_MARGIN = 2
        self.TICK_LABEL_HEIGHT = 50

        self.show_seconds = True
        self.frames_button = QRadioButton('frames')
        self.minutes_seconds_button = QRadioButton('mm:ss')
        self.minutes_seconds_button.setChecked(True)
        self.frames_button.toggled.connect(self.toggle_unit)
        self.minutes_seconds_button.toggled.connect(self.toggle_unit)
        self.initUI()

    def initUI(self):
        self.resize(self.width(),self.HEIGHT)
        # Set Background
        pal = QPalette()
        pal.setColor(QPalette.Background, QColor(20,20,20))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

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
        self.frames_button.setStyleSheet(radio_button_stylesheet)
        self.minutes_seconds_button.setStyleSheet(radio_button_stylesheet)
        button_strip = QHBoxLayout()
        button_strip.addStretch(0)
        button_strip.addWidget(self.frames_button)
        button_strip.addWidget(self.minutes_seconds_button)
        button_strip.addStretch(0)
        button_strip.setSpacing(10)
        button_strip.setContentsMargins(5,0,5,0)
        vbox = QVBoxLayout(self)
        vbox.addStretch(0)
        vbox.addLayout(button_strip)
        vbox.setContentsMargins(0,0,0,5)

    def toggle_unit(self):
        if self.minutes_seconds_button.isChecked(): self.show_seconds=True
        if self.frames_button.isChecked(): self.show_seconds=False
        self.toggle_units_signal.emit(self.show_seconds)
        self.update()

    def get_visible_tick_positions(self):
        if self.show_seconds: spacing_options = self.SECOND_SPACING_OPTIONS
        else: spacing_options = self.FRAME_SPACING_OPTIONS
        visible_range = self.current_range[1]-self.current_range[0]
        best_spacing = np.min(np.nonzero(visible_range/spacing_options < self.MAX_TICKS_VISIBLE)[0])
        tick_interval = spacing_options[best_spacing]
        first_tick = self.current_range[0] - self.current_range[0]%tick_interval + tick_interval
        abs_tick_positions = np.arange(first_tick,self.current_range[1],tick_interval)
        rel_tick_positions = (abs_tick_positions-self.current_range[0])/visible_range*self.width()
        return abs_tick_positions.astype(int),rel_tick_positions.astype(int)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.setPen(QColor(150, 150, 150))
        qp.setFont(QFont("Helvetica [Cronyx]", 10))
        qp.setRenderHint(QPainter.Antialiasing)
        abs_tick_positions,rel_tick_positions = self.get_visible_tick_positions()
        for a,r in zip(abs_tick_positions,rel_tick_positions): 
            label = get_minutes_seconds(a, fps=self.fps) if self.show_seconds else str(a)
            qp.drawLine(r,0,r,self.TICK_HEIGHT)
            qp.drawText(
                r-self.TICK_LABEL_WIDTH//2,
                self.TICK_HEIGHT+self.TICK_LABEL_MARGIN,
                self.TICK_LABEL_WIDTH,
                self.TICK_LABEL_HEIGHT,
                Qt.AlignHCenter, label)
        qp.end()

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.update()


class TrackOverlay(QWidget):
    def __init__(self, trackStack, vlines={}, fps=30):
        super().__init__(parent=trackStack)
        self.trackStack = trackStack
        self.fps = fps
        self.show_seconds = True
        self.vlines = vlines
        self.selection_intervals = []
        self.bounds = trackStack.bounds
        self.current_range = trackStack.current_range
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.CURSOR_LABEL_LEFT_MARGIN = 5
        self.CURSOR_LABEL_BOTTOM_MARGIN = 5
        self.CURSOR_LABEL_HEIGHT = 15
        self.CURSOR_LABEL_WIDTH = 100

    def update_selection_mask(self, selection_mask, bounds):
        diff = np.diff(np.pad(selection_mask, (1,1)))
        starts = (diff>0).nonzero()[0]+bounds[0]
        ends = (diff<0).nonzero()[0]+bounds[0]
        self.selection_intervals = list(zip(starts,ends))
        self.update()

    def paintEvent(self, event):
        self.resize(self.trackStack.size())
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        for key,vline in self.vlines.items():
            qp.setPen(QPen(QColor(*vline['color']),vline['linewidth']))
            r = self.trackStack.abs_to_rel(vline['position'])
            if r > 0 and r < self.width():
                qp.drawLine(r,0,r,self.trackStack.height())

                if key=='cursor' and r < self.width():
                    qp.setFont(QFont("Helvetica [Cronyx]", 12))
                    if self.show_seconds: label = get_minutes_seconds(vline['position'], fps=self.fps)
                    else: label = str(vline['position'])
                    qp.drawText(
                        r+self.CURSOR_LABEL_LEFT_MARGIN,
                        self.height()-self.CURSOR_LABEL_HEIGHT, 
                        self.CURSOR_LABEL_WIDTH,
                        self.height()-self.CURSOR_LABEL_BOTTOM_MARGIN,
                        Qt.AlignLeft, label)
                        

        qp.setPen(QPen(QColor(255,255,255,150), 1))
        qp.setBrush(QBrush(QColor(255,255,255,100), Qt.SolidPattern))
        for s,e in self.selection_intervals:
            s_rel = self.trackStack.abs_to_rel(s)
            e_rel = self.trackStack.abs_to_rel(e)
            if e_rel > 0 or s_rel < self.width() and e_rel > s_rel:
                qp.drawRect(s_rel, 0, e_rel-s_rel, self.height())

        qp.end()

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.update()

    def update_time_unit(self, show_seconds):
        self.show_seconds = show_seconds
        self.update()


class TrackStack(QWidget):
    new_current_position = pyqtSignal(int)
    selection_change = pyqtSignal(list, list)

    def __init__(self, bounds=None, zoom_gain=0.005, min_range=30, fps=30, vlines={}):
        super().__init__()
        assert bounds is not None
        self.fps = fps
        self.bounds = bounds
        self.zoom_gain = zoom_gain
        self.min_range = min_range
        self.current_range = self.bounds
        self.selection_mask = np.zeros(bounds[1]-bounds[0])
        self.selection_drag_mode = 0 # +1 for shift-click, -1 for command-click
        self.selection_drag_initial_position = None

        self.timeline = Timeline(self, fps)
        self.overlay = TrackOverlay(self, vlines=vlines, fps=self.fps)

        self.tracks = [self.timeline]
        self.new_current_position.connect(self.update_current_position)
        self.timeline.toggle_units_signal.connect(self.overlay.update_time_unit)


    def initUI(self, vlines={}):
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        self.setSizePolicy(sizePolicy)

        hbox = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Vertical)
        for track in self.tracks:
            splitter.addWidget(track)
        hbox.addWidget(splitter)
        hbox.setContentsMargins(0, 0, 0, 0)
        self.overlay.vlines['cursor'] = {'position':0, 'color':(250,250,250), 'linewidth':1}
        self.update_current_range()
        self.overlay.raise_()
        self.overlay.update()


    def add_track(self, track):
        self.tracks.insert(0,track)

    def wheelEvent(self,event):
        if np.abs(event.angleDelta().y()) > np.abs(event.angleDelta().x()): 
            # vertical motion -> zoom
            abs_event_pos = self.rel_to_abs(event.x())
            scale_change = max(1+event.angleDelta().y()*self.zoom_gain, self.min_range/(self.current_range[1]-self.current_range[0]))
            new_range = [
                max(int((self.current_range[0]-abs_event_pos)*scale_change+abs_event_pos),self.bounds[0]),
                min(int((self.current_range[1]-abs_event_pos)*scale_change+abs_event_pos),self.bounds[1])]
            self.update_current_range(new_range=new_range)

        if np.abs(event.angleDelta().y()) < np.abs(event.angleDelta().x()): 
            # horizontal motion -> pan
            abs_delta = np.clip((-event.angleDelta().x())/self.width()*(self.current_range[1]-self.current_range[0]),
                self.bounds[0]-self.current_range[0],self.bounds[1]-self.current_range[1])
            new_range = [ int(self.current_range[0]+abs_delta),int(self.current_range[1]+abs_delta)]
            self.update_current_range(new_range=new_range)

        

    def mouseMoveEvent(self, event):
        position = int(self.rel_to_abs(event.x()))
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.selection_drag_move(position, 1)
        elif modifiers == QtCore.Qt.ControlModifier:
            self.selection_drag_move(position, -1)
        elif self.selection_drag_mode == 0:
            self.new_current_position.emit(position)        

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            position = int(self.rel_to_abs(event.x()))
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                self.selection_drag_start(position, 1)
            elif modifiers == QtCore.Qt.ControlModifier:
                self.selection_drag_start(position, -1)
            else:
                self.new_current_position.emit(position)

    def mouseReleaseEvent(self, event):
        self.selection_drag_end()

    def selection_drag_start(self, position, mode):
        self.selection_drag_mode = mode
        self.selection_drag_initial_position = position

    def selection_drag_end(self):
        self.selection_drag_mode = 0
        self.selection_drag_initial_position = None

    def selection_drag_move(self, position, mode):
        if self.selection_drag_mode == mode:
            s,e = sorted([self.selection_drag_initial_position,position])
            self.selection_change.emit([(s,e)], [max(mode,0)])

    def rel_to_abs(self,r):
        return r/self.width()*(self.current_range[1]-self.current_range[0])+self.current_range[0]

    def abs_to_rel(self,a):
        return (a-self.current_range[0])/(self.current_range[1]-self.current_range[0])*self.width()

    def update_current_range(self, new_range=None):
        if new_range is not None: self.current_range = new_range
        for child in self.tracks+[self.overlay]: 
            child.update_current_range(self.current_range)

    def update_current_position(self, position):
        self.overlay.vlines['cursor']['position'] = position
        self.overlay.update()

    def update_selection_mask(self, selection_mask):
        self.selection_mask = selection_mask
        self.overlay.update_selection_mask(self.selection_mask, self.bounds)


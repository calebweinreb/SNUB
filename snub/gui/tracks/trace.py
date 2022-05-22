from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pyqtgraph as pg
import colorsys
import numpy as np
import pickle
import os

from snub.gui.tracks import Track, TrackGroup
from snub.io.project import _random_color

class CheckableComboBox(QComboBox):
    toggleSignal = pyqtSignal(bool, int)
    def __init__(self, width=100):
        super().__init__()
        self.setFixedWidth(width)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def addItem(self, label, color, checked=False):
        super().addItem(label)
        item_index = self.count()-1
        item = self.model().item(item_index,0)
        item.setFlags(Qt.ItemIsEnabled)
        item.setForeground(QColor('black'))
        item.setBackground(QColor(*color))
        if checked: item.setCheckState(Qt.Checked)
        else: item.setCheckState(Qt.Unchecked)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        checked = item.checkState()==Qt.Checked
        self.toggleSignal.emit(not checked, index.row())

    def set_checked(self, index, checked):
        checkState = Qt.Checked if checked else Qt.Unchecked
        self.model().item(index,0).setCheckState(checkState)



class TracePlot(Track):
    visible_traces_signal = pyqtSignal(set)

    def __init__(self, config, data_path=None, data=None, labels=None, bound_rois='',
                 initial_visible_traces=None, controls_padding_right=10, colors={},
                 yaxis_width=30, controls_padding_top=5, trace_label_margin=4, **kwargs):

        super().__init__(config, **kwargs)
        self.controls_padding_right = controls_padding_right
        self.controls_padding_top = controls_padding_top
        self.trace_label_margin = trace_label_margin
        self.bound_rois = None if len(bound_rois)==0 else bound_rois

        if data is not None: self.data = data
        else: self.data = pickle.load(open(os.path.join(config['project_directory'],data_path),'rb'))

        if initial_visible_traces is not None: self.visible_traces = set(initial_visible_traces)
        elif len(self.data)>0: self.visible_traces = set([np.random.choice(list(self.data.keys()))])
        else: self.visible_traces = set([])

        self.colors = dict(colors)
        for label in self.data: 
            if not label in self.colors:
                print('random!')
                self.colors[label] = _random_color()
        
        self.clearButton = QPushButton("Clear")
        self.clearButton.clicked.connect(self.clear)
        self.dropDown = CheckableComboBox()
        self.dropDown.toggleSignal.connect(self.toggle_trace)

        self.plotWidget = pg.plot()
        self.plotWidget.hideAxis('bottom')
        self.plotWidget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.plotWidget.showGrid(x=False, y=True, alpha = 0.5)  
        self.plotWidget.getAxis('left').setWidth(yaxis_width)

        self.label_order = []
        self.trace_labels = []
        for label in self.data:
            self.dropDown.addItem(label, self.colors[label], checked=(label in self.visible_traces))
            trace_label = QPushButton(label)
            trace_label.setFixedWidth(trace_label.fontMetrics().boundingRect(trace_label.text()).width()+20)
            trace_label.setStyleSheet("background-color: rgb(20,20,20); color: rgb({},{},{});".format(*self.colors[label]))
            trace_label.pressed.connect(self.trace_label_button_push)
            #trace_label.setMargin(self.trace_label_margin)
            if not label in self.visible_traces: trace_label.hide()
            self.label_order.append(label)
            self.trace_labels.append(trace_label)
    
        self.initUI()
        self.update_plot()
        

    def trace_label_button_push(self):
        self.hide_trace(self.sender().text())
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.plotWidget)
        self.controls = QWidget(self)
        control_layout = QHBoxLayout(self.controls)
        control_layout.addStretch(0)
        for trace_label in self.trace_labels: control_layout.addWidget(trace_label, alignment=Qt.AlignTop)
        control_layout.addWidget(self.dropDown, alignment=Qt.AlignTop)
        control_layout.addWidget(self.clearButton, alignment=Qt.AlignTop)
        self.update_controls_geometry()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(1,1)
        self.update()

    def clear(self):
        for i in list(self.visible_traces):
            self.hide_trace(i, update_plot=False)
        self.update_plot()

    def toggle_trace(self, state, index):
        label = self.label_order[index]
        if state: self.show_trace(label)
        else: self.hide_trace(label)

    def show_trace(self, label, update_plot=True):
        if not label in self.visible_traces:
            index = self.label_order.index(label)
            self.dropDown.set_checked(index, True)
            self.visible_traces.add(label)
            self.trace_labels[index].show()
            if update_plot: self.update_plot()

    def hide_trace(self, label, update_plot=True):
        if label in self.visible_traces:
            index = self.label_order.index(label)
            self.dropDown.set_checked(index, False)
            self.visible_traces.remove(label)
            self.trace_labels[index].hide()
            if update_plot: self.update_plot()

    def update_plot(self):
        self.plotWidget.clear()
        for label in self.visible_traces:
            self.plotWidget.plot(*self.data[label].T, pen=pg.mkPen(QColor(*self.colors[label])))
        self.visible_traces_signal.emit(self.visible_traces)

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

    def bind_rois(self, roiplot):
        self.visible_traces_signal.connect(roiplot.update_visible_contours)
        self.visible_traces_signal.emit(self.visible_traces)


class HeadedTracePlot(TrackGroup):
    def __init__(self, config, **kwargs):
        trace = TracePlot(config, **kwargs)
        super().__init__(config, tracks={'trace':trace}, track_order=['trace'], **kwargs)


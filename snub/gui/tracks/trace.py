from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pyqtgraph as pg
import colorsys
import numpy as np
import os

from snub.gui.tracks import Track, TrackGroup

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
    def __init__(self, config, data_path=None, binsize=None, labels=None, start_time=0,
                 initial_visible_traces=None, controls_padding_right=10, colors=None,
                 yaxis_width=30, controls_padding_top=5, trace_label_margin=4, **kwargs):

        super().__init__(config, **kwargs)
        self.binsize = binsize
        self.start_time = start_time 
        self.controls_padding_right = controls_padding_right
        self.controls_padding_top = controls_padding_top
        self.trace_label_margin = trace_label_margin

        self.data = np.load(os.path.join(config['project_directory'],data_path))
        if initial_visible_traces is not None: self.visible_traces = set(initial_visible_traces)
        else: self.visible_traces = set([np.random.randint(self.data.shape[0])])

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
        self.plotWidget.setAttribute(Qt.WA_TransparentForMouseEvents)
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


class HeadedTracePlot(TrackGroup):
    def __init__(self, config, **kwargs):
        trace = TracePlot(config, **kwargs)
        super().__init__(config, tracks={'trace':trace}, track_order=['trace'], **kwargs)


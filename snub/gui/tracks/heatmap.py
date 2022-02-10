from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from functools import partial
import os
import cv2
import numpy as np
import cmapy
import time
from numba import njit, prange

from snub.gui.tracks import Track, TracePlot, TrackGroup
from snub.gui.utils import cvImage_to_Qimage, AdjustColormapDialog


@njit
def map_heatmap_by_intervals(data, intervals, min_step):
    intervals = intervals - intervals[0,0]
    num_cols = int(intervals[-1,1]/min_step)
    output = np.zeros((data.shape[0],num_cols))
    for i in prange(intervals.shape[0]):
        start = int(intervals[i,0]/min_step)
        end = int(intervals[i,1]/min_step)
        output[:,start:end] = data[:,i:i+1]
    return output


class HeatmapImage(Track):
    downsample_options=np.array([1,3,10,30,100,300,1000,3000,10000,30000,100000])
    max_display_resolution=2000

    def __init__(self, config, image, start_time, binsize, vertical_range=None, parent=None):
        super().__init__(config, parent=parent)
        self.binsize = binsize
        self.start_time = start_time
        if vertical_range is None: self.vertical_range = [0,image.shape[0]]
        else: self.vertical_range = vertical_range
        self.set_image(image)

    def set_image(self, image):
        self.binned_images = [self.bin_image(image, width) for width in self.downsample_options]

    def bin_image(self, image, width):
        image = image.astype(float)
        cols = int(np.ceil(image.shape[1]/width))
        image_padded = np.pad(image, ((0,0),(0,int(width*cols)-image.shape[1]),(0,0)))
        return np.uint8(image_padded.reshape(image.shape[0],cols,-1,3).mean(2))

    def get_current_pixmap(self):
        ### NOTE: CAN BE ABSTRACTED: SEE SIMILAR TIMELINE METHOD
        visible_bins = (self.current_range[1]-self.current_range[0])/self.binsize
        downsample_ix = np.min(np.nonzero(visible_bins / self.downsample_options < self.max_display_resolution)[0])
        use_image_data = self.binned_images[downsample_ix]
        use_image_data = use_image_data[self.vertical_range[0]:self.vertical_range[1]]
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
        return  QPixmap(cvImage_to_Qimage(use_image_data.astype(np.uint8)))

    def paintEvent(self, event):
        self.resize(self.parent().size())
        qp = QPainter(self)
        pixmap = self.get_current_pixmap().scaled(self.size()) 
        qp.setRenderHint(QPainter.Antialiasing)
        qp.drawPixmap(QPoint(0,0), pixmap)

    def update_vertical_range(self, vrange):
        self.vertical_range = vrange
        self.update()
         


class HeatmapLabels(QWidget):
    max_label_height=20
    label_margin=10

    def __init__(self, labels, label_order=None, label_color=(255,255,255), 
                 label_font_size=12, max_label_width=300, vertical_range=None, parent=None):
        super().__init__(parent=parent)

        self.label_color = label_color
        self.label_font_size = label_font_size
        self.max_label_width = max_label_width
        if vertical_range is None: vertical_range=[0,len(labels)]
        else: self.vertical_range=vertical_range

        self.labels = labels
        if label_order is not None: self.label_order = label_order
        else: self.label_order = np.arange(len(labels))

    def update_label_order(self, label_order):
        self.label_order = label_order
        self.update()

    def update_vertical_range(self, vrange):
        self.vertical_range = vrange
        self.update()

    def paintEvent(self, event):
        self.resize(self.parent().size())
        qp = QPainter(self)
        qp.setPen(QColor(*self.label_color))
        qp.setFont(QFont("Helvetica [Cronyx]", self.label_font_size))
        for height,i in enumerate(self.label_order):
            height = (height+.5-self.vertical_range[0])/(self.vertical_range[1]-self.vertical_range[0])
            if height > 0 and height < 1:
                center_height = height*self.height()
                qp.drawText(self.label_margin, center_height-self.max_label_height//2, 
                self.max_label_width, self.max_label_height, Qt.AlignVCenter, self.labels[i])


class Heatmap(Track):
    display_trace_signal = pyqtSignal(int)
    
    def __init__(self, config, selected_intervals, labels_path=None, data_path=None, row_order_path=None,
                 intervals_path=None, start_time=0, colormap='viridis', max_label_width=300, show_labels=False,
                 label_color=(255,255,255), label_font_size=12, vmin=0, vmax=1, add_traceplot=False, 
                 vertical_range=None, **kwargs):
        super().__init__(config, **kwargs)

        self.selected_intervals = selected_intervals
        self.vmin,self.vmax = vmin,vmax
        self.colormap = colormap
        self.show_labels = show_labels
        self.add_traceplot = add_traceplot
        self.min_step = config['min_step']

        self.data = np.load(os.path.join(config['project_directory'],data_path))
        self.intervals = np.load(os.path.join(config['project_directory'],intervals_path))
        self.start_time = self.intervals[0,0]
        if labels_path is None: self.labels = [str(i) for i in range(self.data.shape[0])]
        else: self.labels = open(os.path.join(config['project_directory'],labels_path),'r').read().split('\n')
        if row_order_path is None: self.row_order = np.arange(self.data.shape[0])
        else: self.row_order = np.load(os.path.join(config['project_directory'],row_order_path))
        self.initial_row_order = self.row_order.copy()
        if vertical_range is None: self.vertical_range = [0,self.data.shape[0]]
        else: self.vertical_range = vertical_range
        self.adjust_colormap_dialog = AdjustColormapDialog(self, self.vmin, self.vmax)
        self.adjust_colormap_dialog.new_range.connect(self.update_colormap_range)
        self.heatmap_image = HeatmapImage(config, image=self.get_image_data(), start_time=start_time, 
                                          binsize=self.min_step, vertical_range=self.vertical_range, parent=self)
        
        self.heatmap_labels = HeatmapLabels(self.labels, label_order=self.row_order, label_color=label_color, 
                                            vertical_range=self.vertical_range, max_label_width=max_label_width, parent=self)
                                            
        

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.heatmap_image.update_current_range(current_range)


    def contextMenuEvent(self, event):
        menu_options = [('Adjust colormap range', self.show_adjust_colormap_dialog),
                        ('Reorder by selection', self.reorder_by_selection),
                        ('Restore original order', self.restore_original_order)]

        if self.add_traceplot:
            y = event.y()/self.height()*(self.vertical_range[1]-self.vertical_range[0])+self.vertical_range[0]
            trace_index = self.row_order[int(y)]
            display_trace_slot = lambda: self.display_trace_signal.emit(trace_index)
            menu_options.insert(0,('Dislay trace {}'.format(trace_index), display_trace_slot))

        contextMenu = QMenu(self)
        for name,slot in menu_options:
            label = QLabel(name)
            action = QWidgetAction(self)
            action.setDefaultWidget(label)
            action.triggered.connect(slot)
            contextMenu.addAction(action)

        button_options = [('Zoom in (vertical)', self.zoom_in_vertical),
                          ('Zoom out (vertical)', self.zoom_out_vertical),
                          ('Shift up', self.shift_up),
                          ('Shift down', self.shift_down)]

        for name,slot in button_options:
            button = QPushButton(name)
            action = QWidgetAction(self)
            action.setDefaultWidget(button)
            button.clicked.connect(slot)
            contextMenu.addAction(action)

        contextMenu.setStyleSheet("""
            QLabel, QPushButton { background-color : #3E3E3E; padding: 10px 12px 10px 12px;}
            QLabel:hover, QPushButton:hover { background-color: #999999;} """)
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

    def reorder_by_selection(self):
        weights = self.selected_intervals.intersection_proportions(self.intervals)
        activation = (self.data * weights).sum(1)
        self.update_row_order(np.argsort(activation)[::-1])

    def restore_original_order(self):
        self.update_row_order(self.initial_row_order)

    def update_row_order(self, order):
        self.row_order = order
        self.update_image_data()
        self.heatmap_labels.update_label_order(order)
 
    def update_image_data(self):
        image_data = self.get_image_data()
        self.heatmap_image.set_image(image_data)

    def get_image_data(self):
        t = time.time()
        data_remapped = map_heatmap_by_intervals(self.data, self.intervals, self.min_step)
        print('a',time.time()-t)
        t = time.time()
        data_scaled = np.clip((data_remapped[self.row_order]-self.vmin)/(self.vmax-self.vmin),0,1)*255
        image_data = cv2.applyColorMap(data_scaled.astype(np.uint8), cmapy.cmap(self.colormap))[:,:,::-1]
        print('b',time.time()-t)
        return image_data

    def update_colormap_range(self, vmin, vmax):
        self.vmin,self.vmax = vmin,vmax
        self.update_image_data()

    def show_adjust_colormap_dialog(self):
        self.adjust_colormap_dialog.show()


    def zoom_out_vertical(self):
        center = np.mean(self.vertical_range)
        width = (self.vertical_range[1]-self.vertical_range[0])
        new_width = width * 2
        new_vrange = [center-new_width/2,center+new_width/2]
        new_vrange = np.around(np.clip(new_vrange,0,self.data.shape[0])).astype(int)
        self.vertical_range = new_vrange
        self.heatmap_image.update_vertical_range(self.vertical_range)
        self.heatmap_labels.update_vertical_range(self.vertical_range)

    def zoom_in_vertical(self):
        center = np.mean(self.vertical_range)
        width = (self.vertical_range[1]-self.vertical_range[0])
        new_width = max(width * .5,10)
        new_vrange = [center-new_width/2,center+new_width/2]
        new_vrange = np.around(np.clip(new_vrange,0,self.data.shape[0])).astype(int)
        self.vertical_range = new_vrange
        self.heatmap_image.update_vertical_range(self.vertical_range)
        self.heatmap_labels.update_vertical_range(self.vertical_range)


    def shift_down(self):
        target_shift = (self.vertical_range[1]-self.vertical_range[0])/2
        max_shift = self.data.shape[0]-self.vertical_range[1]
        shift = int(min(target_shift, max_shift))
        new_vrange = [self.vertical_range[0]+shift, self.vertical_range[1]+shift]
        self.vertical_range = new_vrange
        self.heatmap_image.update_vertical_range(self.vertical_range)
        self.heatmap_labels.update_vertical_range(self.vertical_range)

    def shift_up(self):
        target_shift = (self.vertical_range[1]-self.vertical_range[0])/2
        max_shift = self.vertical_range[0]
        shift = int(min(target_shift, max_shift))
        new_vrange = [self.vertical_range[0]-shift, self.vertical_range[1]-shift]
        self.vertical_range = new_vrange
        self.heatmap_image.update_vertical_range(self.vertical_range)
        self.heatmap_labels.update_vertical_range(self.vertical_range)



class HeadedHeatmap(TrackGroup):
    def __init__(self, config, selected_intervals, **kwargs):
        heatmap = Heatmap(config, selected_intervals, **kwargs)
        super().__init__(config, tracks={'heatmap':heatmap}, track_order=['heatmap'], **kwargs)


class HeatmapTraceGroup(TrackGroup):
    def __init__(self, config, selected_intervals, trace_height_ratio=1, 
                 heatmap_height_ratio=2, height_ratio=1, **kwargs):

        heatmap = Heatmap(config, selected_intervals, height_ratio=heatmap_height_ratio, **kwargs)
        x = heatmap.intervals.mean(1)
        trace_data = {l:np.vstack((x,d)).T for l,d in zip(heatmap.labels, heatmap.data)}
        trace = TracePlot(config, height_ratio=trace_height_ratio, data=trace_data, **kwargs)

        height_ratio = trace_height_ratio+heatmap_height_ratio
        super().__init__(config, tracks={'trace':trace, 'heatmap':heatmap}, 
                    track_order=['trace','heatmap'], height_ratio=height_ratio, **kwargs)
        heatmap.display_trace_signal.connect(trace.show_trace)

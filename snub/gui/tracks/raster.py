from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from functools import partial
import os
import cv2
import numpy as np
import cmapy
import time

from snub.gui.tracks import Track, TraceTrack, TrackGroup







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



class RasterTrack(Track):
    display_trace_signal = pyqtSignal(int)
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
        pixmap = self.get_current_pixmap().scaled(self.size()) #, transformMode=Qt.SmoothTransformation)

        qp.setRenderHint(QPainter.Antialiasing)
        qp.drawPixmap(QPoint(0,0), pixmap)
        qp.setPen(QColor(*self.label_color))
        qp.setFont(QFont("Helvetica [Cronyx]", self.label_font_size))
        for i,label in enumerate(self.labels):
            height = (self.row_order==i).nonzero()[0][0]
            center_height = (height+.5)/self.data.shape[0]*self.height()
            qp.drawText(self.label_margin, center_height-self.max_label_height//2, 
                self.max_label_width, self.max_label_height, Qt.AlignVCenter, label)


class RasterTraceTrack(TrackGroup):
    def __init__(self, config, selected_intervals, trace_height_ratio=1, raster_height_ratio=2, **kwargs):
        self.height_ratio = trace_height_ratio + raster_height_ratio
        trace = TraceTrack(config, height_ratio=trace_height_ratio, **kwargs)
        raster = RasterTrack(config, selected_intervals, height_ratio=raster_height_ratio, **kwargs)
        height_ratio = trace_height_ratio+raster_height_ratio
        super().__init__(config, tracks={'trace':trace, 'raster':raster}, 
                    track_order=['trace','raster'], height_ratio=height_ratio, **kwargs)
        raster.display_trace_signal.connect(trace.show_trace)

import numpy as np
from ncls import NCLS
from numba import njit, prange
import os
from pyqtgraph import VerticalLabel
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

'''
Timeline-related
'''

def time_to_position(current_range, width, t):
    pos_rel = (t - current_range[0]) / (current_range[1]-current_range[0])
    return pos_rel * width

def position_to_time(current_range, width, p):
    return p/width * (current_range[1]-current_range[0]) + current_range[0]



'''
Image-related
'''

def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    if isinstance(image.flat[0], np.floating):
        image = float_to_uint8(image)
    H, W, C = int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
    if C == 4:
        format = QImage.Format_RGBA8888
    elif C == 3:
        format = QImage.Format_RGB888
    else:
        raise ValueError('Aberrant number of channels: {}'.format(C))
    qpixmap = QPixmap(QImage(image, W,
                                         H, image.strides[0],
                                         format))
    return qpixmap


def float_to_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.float:
        image = (image * 255).clip(min=0, max=255).astype(np.uint8)
    return image


'''
For quickly finding intervals overlaps. Used to store the currently selected intervals
'''

@njit 
def sum_by_index(x, ixs, n):
    out = np.zeros(n)
    for i in prange(len(ixs)):
        out[ixs[i]] += x[i]
    return out



class SelectionIntervals():
    def __init__(self, timestep):
        self.timestep = timestep
        self.intervals = np.empty((0,2))

        
    def partition_intervals(self, start, end):
        ends_before = self.intervals[:,1] < start
        ends_after = self.intervals[:,1] >= start
        starts_before = self.intervals[:,0] <= end
        starts_after = self.intervals[:,0] > end
        intersect = self.intervals[np.bitwise_and(ends_after, starts_before)]
        pre = self.intervals[ends_before]
        post = self.intervals[starts_after]
        return pre,intersect,post
        
        
    def add_interval(self, start, end):
        pre,intersect,post = self.partition_intervals(start,end)
        if intersect.shape[0] > 0:
            merged_start = np.minimum(intersect[0,0],start)
            merged_end = np.maximum(intersect[-1,1],end)
        else: 
            merged_start, merged_end = start, end
        merged_interval = np.array([merged_start, merged_end]).reshape(1,2)
        self.intervals = np.vstack((pre, merged_interval, post))

    def remove_interval(self, start, end):
        pre,intersect,post = self.partition_intervals(start,end)
        pre_intersect = np.empty((0,2))
        post_intersect = np.empty((0,2))
        if intersect.shape[0] > 0:
            if intersect[0,0] < start: pre_intersect = np.array([intersect[0,0],start])
            if intersect[-1,1] > end: post_intersect = np.array([end,intersect[-1,1]])
        self.intervals = np.vstack((pre,pre_intersect,post_intersect,post))
        
    def preprocess_for_ncls(self, intervals):
        intervals_discretized = (intervals/self.timestep).astype(int)
        return (intervals_discretized[:,0].copy(order='C'),
                intervals_discretized[:,1].copy(order='C'),
                np.arange(intervals_discretized.shape[0]))
        
    def intersection_proportions(self, query_intervals): 
        query_intervals = self.preprocess_for_ncls(query_intervals)
        selection_intervals = self.preprocess_for_ncls(self.intervals)
        ncls = NCLS(*selection_intervals)
        query_ixs, selection_ixs = ncls.all_overlaps_both(*query_intervals)
        if len(query_ixs)>0:
            intersection_starts = np.maximum(query_intervals[0][query_ixs], selection_intervals[0][selection_ixs])
            intersection_ends = np.minimum(query_intervals[1][query_ixs], selection_intervals[1][selection_ixs])
            intersection_lengths = intersection_ends - intersection_starts
            query_intersection_lengths = sum_by_index(intersection_lengths, query_ixs, len(query_intervals[0]))
            query_lengths = query_intervals[1] - query_intervals[0] + 1e-10
            return query_intersection_lengths / query_lengths
        else:
            return np.zeros(len(query_intervals[0]))


'''
Widget with header bar containing title and minimize/maximize buttons. 
Mixin can be applied to objects that satisfy ALL the following:
    - parent is a QSplitter widget

'''

class HeaderMixin():

    def initUI(self, name='', initial_visibility=True, initial_saved_size=200, 
               header_height=20, orientation='horizontal', min_size_at_show=100,
               **kwargs):

        self.name = name
        self.saved_size = initial_saved_size
        self.is_visible = initial_visibility
        self.min_size_at_show = min_size_at_show
        self.header_height = header_height
        self.toggle_button = QPushButton()
        self.toggle_button.clicked.connect(self.toggle_visiblity)

        self.title = VerticalLabel(name, orientation='horizontal')
        self.header = QWidget(objectName="trackGroup_header")
        self.header_layout = QBoxLayout(QBoxLayout.LeftToRight, self.header)
        self.header_layout.addStretch(0)
        self.header_layout.addWidget(self.title)
        self.header_layout.addStretch(0)
        self.header_layout.addWidget(self.toggle_button)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.header)

        self.plus_icon = QIcon(QPixmap(os.path.join(os.path.dirname(os.path.realpath(__file__)),'icons','plus.png')))
        self.minus_icon = QIcon(QPixmap(os.path.join(os.path.dirname(os.path.realpath(__file__)),'icons','minus.png')))
        self.toggle_button.setIcon(self.plus_icon)
        self.toggle_button.setIconSize(QSize(12,12))

        self.setStyleSheet("QWidget#trackGroup_header { background-color: rgb(30,30,30); }")
        self.header.setStyleSheet("QPushButton { color: rgb(150,150,150); border: 0px;}")
        self.update_layout()


    def toggle_visiblity(self):
        if self.is_visible:
            self.save_current_size()
            self.is_visible = False
        else: self.is_visible = True
        self.update_layout()

    def set_header_orientation(self, orientation):
        self.setMaximumSize(10000,10000)
        self.setMinimumSize(0,0)
        self.header.setMaximumSize(10000,10000)
        self.header.setMinimumSize(0,0)
        self.title.setOrientation(orientation)
        if orientation=='horizontal':
            self.header.setFixedHeight(self.header_height)
            self.header_layout.setContentsMargins(10, 0, 10, 0)
            self.header_layout.setDirection(QBoxLayout.LeftToRight)
            if not self.is_visible: self.setFixedHeight(self.header_height)
        if orientation=='vertical':
            self.header.setFixedWidth(self.header_height)
            self.header_layout.setContentsMargins(0, 10, 0, 10)
            self.header_layout.setDirection(QBoxLayout.BottomToTop)
            if not self.is_visible: self.setFixedWidth(self.header_height)

    def save_current_size(self):
        splitter = self.parent()
        if splitter is not None and self.is_visible:
            self.saved_size = splitter.sizes()[splitter.indexOf(self)]

    def update_layout(self):
        if self.is_visible:
            self.toggle_button.setIcon(self.minus_icon)
            self.set_size(max(self.saved_size,self.min_size_at_show))
            for i in range(1,self.layout.count()):
                self.layout.itemAt(i).widget().show()
                self.set_header_orientation('horizontal')
        else:
            self.toggle_button.setIcon(self.plus_icon)
            for i in range(1,self.layout.count()):
                self.layout.itemAt(i).widget().hide()
            splitter = self.parent()
            if splitter is not None:
                if splitter.orientation()==Qt.Horizontal: header_orientation = 'vertical'
                if splitter.orientation()==Qt.Vertical: header_orientation = 'horizontal'
                self.set_header_orientation(header_orientation)

    def set_size(self, size):
        splitter = self.parent()
        if splitter is not None:
            index = splitter.indexOf(self)
            sizes = splitter.sizes()
            current_remainder = sum(sizes)-sizes[index]
            if current_remainder > 0:
                new_remainder = sum(sizes)-size
                sizes = [int(s*new_remainder/current_remainder) for s in sizes]
                sizes[index] = int(size)
                splitter.setSizes(sizes)








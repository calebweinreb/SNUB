import numpy as np
from ncls import NCLS
from numba import njit, prange
from PyQt5 import QtGui


# timeline-related

def time_to_position(current_range, width, t):
    pos_rel = (t - current_range[0]) / (current_range[1]-current_range[0])
    return pos_rel * width

def position_to_time(current_range, width, p):
    return p/width * (current_range[1]-current_range[0]) + current_range[0]




# image-related

def numpy_to_qpixmap(image: np.ndarray) -> QtGui.QPixmap:
    if isinstance(image.flat[0], np.floating):
        image = float_to_uint8(image)
    H, W, C = int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
    if C == 4:
        format = QtGui.QImage.Format_RGBA8888
    elif C == 3:
        format = QtGui.QImage.Format_RGB888
    else:
        raise ValueError('Aberrant number of channels: {}'.format(C))
    qpixmap = QtGui.QPixmap(QtGui.QImage(image, W,
                                         H, image.strides[0],
                                         format))
    return qpixmap


def float_to_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.float:
        image = (image * 255).clip(min=0, max=255).astype(np.uint8)
    return image



# for quickly finding intervals overlaps
# used to store the currently selected intervals



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


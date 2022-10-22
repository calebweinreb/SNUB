"""
This file implements the NWBTree, a convenience class that
makes it simpler to recursively crawl through an NWB file.
"""

import numpy as np

from pynwb import NWBFile, TimeSeries
from pynwb.core import MultiContainerInterface
from pynwb.image import ImageSeries

"""
Below we attempt to import some optional NWB extensions for
storing keypoint data and behavioral labels. Each import
will be skipped if the imported NWB extension is not installed,
at which point it will be assumed that the NWB file being
wrapped does not make use of the corresponding extension.

https://github.com/ndx-complex-behavior/

In general, an NWB file cannot be accessed if the relevant
extension is not available, so this file should be modified to
support more nwb extensions.
"""

try:
    from ndx_pose import PoseEstimation
except ModuleNotFoundError:
    PoseEstimation = None
    
try:
    from ndx_labels import LabelSeries
except ModuleNotFoundError:
    LabelSeries = None


class NWBTree:
    """
    Tree data structure that wraps an NWB file to simplify
    traversal of the file structure.

    Parameters
    ----------
    obj
        Some node in the NWB file structure.
    """
    def __init__(self, obj):
        self.obj = obj
    
    """
    Methods for determining the type of node at
    the root of the tree.
    """
    def is_root(self):
        return _is_nwb_file(self.obj)
    
    def is_module(self):
        return _is_module(self.obj)
    
    def is_leaf(self):
        return _is_timeseries(self.obj) 
    
    def is_video(self):
        return _is_video(self.obj)
    
    def is_keypoints(self):
        return _is_keypoints(self.obj)
    
    def is_labels(self):
        return _is_labels(self.obj)
    
    """
    Methods for traversing the tree.
    """
    def keys(self):
        if self.is_leaf():
            self._raise_leaf_error()
        elif self.is_root():
            return ['acquisition', 'processing']
        elif self.is_keypoints():
            return self.obj.pose_estimation_series.keys()
        elif self.is_module():
            return self.obj.data_interfaces.keys()
        else:    # either processing or acquisition
            return self.obj.keys()
        
    def values(self):
        return [self[key] for key in self.keys()]

    def items(self):
        return [(key, self[key]) for key in self.keys()]
    
    def __iter__(self):
        return self.keys()
    
    def __len__(self):
        return len(self.keys())

    """
    Methods for retrieving the data at the present node.
    """
    def _raise_leaf_error(self):
        raise KeyError('Cannot index a leaf node!')

    def get_data(self, dtype=float):
        assert self.is_leaf()
        return self.obj.data[:].astype(dtype)
        
    def get_timestamps(self):
        assert self.is_leaf()
        return _get_timestamps(self.obj)
    
    def get_both(self, dtype=float):
        data = self.get_data(dtype)
        timestamps = self.get_timestamps()
        return data, timestamps
    
    def __getitem__(self, key):
        if self.is_leaf():
            raise self._raise_leaf_error()
        elif self.is_root():
            if key == 'acquisition':
                return NWBTree(self.obj.acquisition)
            elif key == 'processing':
                return NWBTree(self.obj.processing)
            else:
                raise KeyError('Key must be "processing" or "acquisition".')
        elif self.is_keypoints():
            return NWBTree(self.obj.pose_estimation_series[key])
        else:
            return NWBTree(self.obj[key])


def _get_timestamps(ts):
    """
    Given a time series object, returns the timestamps for
    the datapoints it contains.

    Parameters
    ----------
    ts : TimeSeries
        NWB TimeSeries object.
    """
    if ts.timestamps is None:
        T = len(ts.data)
        try:
            start = ts.start
        except AttributeError:
            start = ts.starting_time
        rate = ts.rate
        stamps = start + np.arange(T) / rate
    else:
        stamps = ts.timestamps[:]
    stamps = stamps.astype(float)
    return stamps

# Methods for determining the type of data stored at the current node
def _is_nwb_file(obj):
    return isinstance(obj, NWBFile)

def _is_module(obj):
    return isinstance(obj, MultiContainerInterface)

def _is_timeseries(obj):
    return isinstance(obj, TimeSeries)

def _is_video(obj):
    return isinstance(obj, ImageSeries)

def _is_keypoints(obj):
    return PoseEstimation and isinstance(obj, PoseEstimation)

def _is_labels(obj):
    return LabelSeries and isinstance(obj, LabelSeries)

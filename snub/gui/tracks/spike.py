from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from functools import partial
import os
import numpy as np
import cmapy
import time

from vispy.scene import SceneCanvas
from vispy.scene.visuals import Markers, Line
from snub.gui.tracks import Track, TracePlot, TrackGroup, Heatmap


'''
class SpikePlot(Heatmap):
    def __init__(self, config, selected_intervals, spikes_path=None, heatmap_path=None, **kwargs):
        print(spikes_path, heatmap_path)
        super().__init__(config, selected_intervals, data_path=heatmap_path, **kwargs)
        self.spike_data = np.load(os.path.join(config['project_directory'],spikes_path))
'''


class SpikePlot(Heatmap):
    def __init__(self, config, selected_intervals, spikes_path=None, markersize=5,
                       heatmap_path=None, heatmap_range=60, colormap='viridis', **kwargs):

        super().__init__(config, selected_intervals, data_path=heatmap_path, **kwargs)
        self.heatmap_range = heatmap_range
        spike_data = np.load(os.path.join(config['project_directory'],spikes_path))
        self.spike_times,self.spike_labels = spike_data[:,0], spike_data[:,1].astype(int)
        self.max_label = self.spike_labels.max()
        self.markersize=markersize
        self.colormap = colormap
        self.cmap = cmapy.cmap(self.colormap).squeeze()[:,::-1].astype(np.float32)/255
        self.canvas = SceneCanvas(self, keys='interactive', bgcolor=self.cmap[0], show=True)
        self.viewbox = self.canvas.central_widget.add_grid().add_view(row=0, col=0, camera='panzoom')
        line_verts = np.vstack([
            np.ones(self.max_label)*self.spike_times.min()-10,
            np.arange(self.max_label),
            np.ones(self.max_label)*self.spike_times.max()+10,
            np.arange(self.max_label)]).T
        self.lines = Line(pos=line_verts.reshape(-1,2), color=np.clip(self.cmap[0]+.1,0,1), method='gl', width=0.5, connect='segments')
        self.viewbox.add(self.lines)

        self.scatter = Markers()
        self.scatter.antialias = 0
        self.scatter.order = -1
        self.set_scatter_data()
        self.viewbox.add(self.scatter)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.canvas.native, 1)
        self.heatmap_image.raise_()
        self.heatmap_labels.raise_()
        self.update_current_range(self.current_range)

    def update_current_range(self, current_range):
        super().update_current_range(current_range)
        if (self.current_range[1]-self.current_range[0]) >= self.heatmap_range:
            self.heatmap_image.show()
        else:
            self.heatmap_image.hide()
            self.viewbox.camera.set_range(x=self.current_range, y=self.get_ylim(), margin=1e-10)
            bgcolor = self.cmap[0]*(self.current_range[1]-self.current_range[0])/self.heatmap_range
            self.canvas.bgcolor = bgcolor
            self.lines.set_data(color=np.clip(bgcolor+.1,0,1))

    def spike_coordinates(self):
        ycoords = self.max_label-np.argsort(self.row_order)[self.spike_labels]+.5
        return np.vstack((self.spike_times,ycoords)).T

    def spike_colors(self):
        image_data = self.get_image_data()
        rows = np.argsort(self.row_order)[self.spike_labels]
        cols = np.around((self.spike_times-self.intervals[0,0])/self.min_step).astype(int)
        colors = image_data[rows,np.clip(cols,0,image_data.shape[1]-1)].astype(np.float32)/255
        return colors

    def zoom_in_vertical(self):
        super().zoom_in_vertical()
        self.viewbox.camera.set_range(x=self.current_range, y=self.get_ylim(), margin=1e-10)

    def zoom_vertical(self,origin,scale_factor):
        super().zoom_vertical(origin,scale_factor)
        self.viewbox.camera.set_range(x=self.current_range, y=self.get_ylim(), margin=1e-10)

    def get_ylim(self):
    	return self.max_label - np.array(self.vertical_range)[::-1] + 1

    def set_scatter_data(self):
        xy = self.spike_coordinates()
        c = self.spike_colors()
        self.scatter.set_data(xy, edge_width=0, face_color=c, edge_color=None, symbol='vbar', size=self.markersize)

    def update_row_order(self, order):
        super().update_row_order(order)
        self.set_scatter_data()

    def update_colormap_range(self, *args):
        super().update_colormap_range(*args)
        self.set_scatter_data()






class HeadedSpikePlot(TrackGroup):
    def __init__(self, config, selected_intervals, **kwargs):
        spikeplot = SpikePlot(config, selected_intervals, **kwargs)
        super().__init__(config, tracks={'spikeplot':spikeplot}, track_order=['spikeplot'], **kwargs)


class SpikePlotTraceGroup(TrackGroup):
    def __init__(self, config, selected_intervals, trace_height_ratio=1, 
                 heatmap_height_ratio=2, height_ratio=1, **kwargs):
        self.height_ratio = trace_height_ratio + heatmap_height_ratio

        spikeplot = SpikePlot(config, selected_intervals, height_ratio=heatmap_height_ratio, **kwargs)

        x = spikeplot.intervals.mean(1)
        trace_data = {l:np.vstack((x,d)).T for l,d in zip(spikeplot.labels, spikeplot.data)}
        trace = TracePlot(config, height_ratio=trace_height_ratio, data=trace_data, **kwargs)

        super().__init__(config, tracks={'trace':trace, 'spikeplot':spikeplot}, 
                    track_order=['trace','spikeplot'], height_ratio=height_ratio, **kwargs)
        spikeplot.display_trace_signal.connect(trace.show_trace)

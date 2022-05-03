from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
import time
import os
import cmapy
import cv2
from scipy.sparse import csc_matrix
from functools import partial

from vispy.scene import SceneCanvas
from vispy.scene.visuals import Image, Line

from snub.gui.panels import Panel
from snub.gui.utils import HeaderMixin, IntervalIndex, AdjustColormapDialog
from snub.io.project import _random_color



class ROIPanel(Panel, HeaderMixin):
    eps = 1e-10

    def __init__(self, config, rois_path=None, data_path=None, labels_path=None, 
                 intervals_path=None, colors={}, linewidth=3, colormap='gray', 
                 initial_selected_rois=[], display_normalized=True, 
                 vmin=None, vmax=None, **kwargs):

        super().__init__(config, **kwargs)

        self.colormap = colormap
        self.linewidth = linewidth
        self.vmin,self.vmax = vmin,vmax
        self.display_normalized = display_normalized
        self.current_frame_index = None

        self.data = np.load(os.path.join(config['project_directory'],data_path))
        self.rois = np.load(os.path.join(config['project_directory'],rois_path))
        self.intervals = np.load(os.path.join(config['project_directory'],intervals_path))
        if labels_path is None: self.labels = [str(i) for i in range(self.data.shape[0])]
        else: self.labels = open(os.path.join(config['project_directory'],labels_path),'r').read().split('\n')
        self.dims = self.rois.shape[1:]
        
        self.colors = dict(colors)
        for label in self.labels: 
            if not label in self.colors:
                self.colors[label] = _random_color()

        self.contour_coordinates = {l:xys for l,xys in zip(self.labels,self.roi_contours(self.rois))}
        self.rois_sparse = csc_matrix(self.rois.reshape(self.rois.shape[0],-1))
        self.rois_maxs = self.rois.max((1,2))+1e-6
        
        self.adjust_colormap_dialog = AdjustColormapDialog(self, self.vmin, self.vmax)
        self.adjust_colormap_dialog.new_range.connect(self.update_colormap_range)

        self.canvas = SceneCanvas(self, keys='interactive', show=True)
        self.canvas.events.mouse_release.connect(self.mouse_release)
        self.viewbox = self.canvas.central_widget.add_grid().add_view(row=0, col=0, camera='panzoom')
        self.viewbox.camera.set_range(x=(0,self.dims[1]), y=(0,self.dims[0]), margin=0)
        self.viewbox.camera.aspect=1

        self.image = Image(np.zeros(self.dims,dtype=np.float32), cmap=colormap, parent=self.viewbox.scene)
        self.contours = {l: Line(self.contour_coordinates[l], color=np.array(self.colors[l])/255, 
            width=self.linewidth, connect='strip', parent=None) for l in self.labels}

        self.viewbox.add(self.image)
        self.update_current_time(config['init_current_time'])
        self.initUI(**kwargs)

    def initUI(self, **kwargs):
        super().initUI(**kwargs)
        self.layout.addWidget(self.canvas.native)
        for c in self.contours.values(): c.order=0
        self.image.order = 1

    def update_current_time(self, t):
        ix = self.intervals[:,1].searchsorted(t)
        if ix < self.intervals.shape[0] and self.intervals[ix,0] <= t and t <= self.intervals[ix,1]:
            self.current_frame_index = ix
        else: self.current_frame_index = None
        self.update_image()

    def update_image(self):
        if self.current_frame_index is None: x = np.zeros(self.rois.shape[0])
        else: x = self.data[:,self.current_frame_index]
        if self.display_normalized: x = x / self.rois_maxs
        rois_sparse = self.rois_sparse.copy()
        rois_sparse.data *= x[rois_sparse.indices]
        image = rois_sparse.sum(0).base.reshape(*self.dims)
        image = (np.clip(image, self.vmin, self.vmax)-self.vmin)/(self.vmax-self.vmin)
        self.image.set_data(image.astype(np.float32))
        self.canvas.update()

    def update_colormap_range(self, vmin, vmax):
        self.vmin,self.vmax = vmin,vmax
        self.update_image()

    def show_adjust_colormap_dialog(self):
        self.adjust_colormap_dialog.show()

    def update_visible_contours(self, visible_contours):
        for l,c in self.contours.items():
            if l in visible_contours:
                c.parent = self.viewbox.scene
            else: c.parent = None

    def roi_contours(self, rois, threshold_max_ratio=0.2, blur_kernel=2):
        contour_coordinates = []
        for roi in rois:
            roi_blur = cv2.GaussianBlur(roi,(11,11),blur_kernel)
            roi_mask = roi_blur > roi_blur.max()*threshold_max_ratio
            xy = cv2.findContours(roi_mask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0][0].squeeze()
            contour_coordinates.append(np.vstack((xy,xy[:1])))
        return contour_coordinates

    def mouse_release(self, event):
        if event.button == 2: self.context_menu(event)

    def context_menu(self, event):
        contextMenu = QMenu(self)
        def add_menu_item(name, slot, item_type='label'):
            action = QWidgetAction(self)
            if item_type=='checkbox': 
                widget = QCheckBox(name)
                widget.stateChanged.connect(slot)
            elif item_type=='label': 
                widget = QLabel(name)
                action.triggered.connect(slot)
            action.setDefaultWidget(widget)
            contextMenu.addAction(action)  
            return widget

        # click to show adjust colormap range dialog
        label = add_menu_item('Adjust colormap range',self.show_adjust_colormap_dialog)

        contextMenu.setStyleSheet("""
            QMenu::item, QLabel, QCheckBox { background-color : #3E3E3E; padding: 5px 6px 5px 6px;}
            QMenu::item:selected, QLabel:hover, QCheckBox:hover { background-color: #999999;}
            QMenu::separator { background-color: rgb(20,20,20);} """)
        action = contextMenu.exec_(event.native.globalPos())
 
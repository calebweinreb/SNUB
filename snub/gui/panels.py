from PyQt5.QtCore import QDir, Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from pyqtgraph.GraphicsScene.mouseEvents import MouseDragEvent
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
from ncls import NCLS
import pyqtgraph as pg
import sys, os, cv2, json
import numpy as np
import cmapy
import time
import cv2
from vidio import VideoReader

'''
Video code was borrowed and modified from 
https://github.com/jbohnslav/pose_annotator/blob/master/pose_annotator/gui/custom_widgets.py
'''

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



class VideoFrame(QtWidgets.QGraphicsView):
    new_current_time = pyqtSignal(float)
    selection_change = pyqtSignal(list,list)
    def __init__(self, config, video_path=None, timestamps_path=None, name=""):
        super().__init__()
        self.initUI()
        self.name = name
        self.vid = VideoReader(os.path.join(config['project_directory'],video_path))
        self.timestamps = np.load(os.path.join(config['project_directory'],timestamps_path))
        self.update_current_time(config['current_time'])
        self.fitInView()
        self.update()

    def initUI(self):  
        self.scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self._photo)
        self.setScene(self.scene)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        self.setSizePolicy(sizePolicy)
        self.grabGesture(Qt.PinchGesture)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setStyleSheet("background:transparent;")
        self.setMouseTracking(True)  
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def event(self, event):
        out = super(VideoFrame, self).event(event)
        if type(event)==QtWidgets.QGestureEvent:
            gesture = event.gesture(Qt.PinchGesture)
            scale = gesture.scaleFactor()
            self.scale(scale, scale)
        return out

    def update_current_time(self, t):
        self.frame = self.vid[self.timestamps.searchsorted(t)]
        self.show_image(self.frame)
        
    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.scene.setSceneRect(rect)
            # if self.hasPhoto():
            unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
            self.scale(1 / unity.width(), 1 / unity.height())
            viewrect = self.viewport().rect()
            scenerect = self.transform().mapRect(rect)
            factor = min(viewrect.width() / scenerect.width(),
                         viewrect.height() / scenerect.height())
            self.scale(factor, factor)
            self._zoom = 0


    def show_image(self, array):
        qpixmap = numpy_to_qpixmap(array)
        # THIS LINE CHANGES THE SCENE WIDTH AND HEIGHT
        self._photo.setPixmap(qpixmap)
        self.update()

    def update_selected_intervals(self):
        pass


class SelectionRectangle(pg.GraphicsObject):
    def __init__(self, topLeft=(0,0), size=(0,0)):
        pg.GraphicsObject.__init__(self)
        self.topLeft = topLeft
        self.size = size
        self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        p.setBrush(pg.mkBrush((255,255,255,50)))
        tl = QtCore.QPointF(self.topLeft[0], self.topLeft[1])
        size = QtCore.QSizeF(self.size[0], self.size[1])
        p.drawRect(QtCore.QRectF(tl, size))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def update_location(self, topLeft, size):
        self.topLeft = topLeft
        self.size = size
        self.generatePicture()

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())



class ScrubbableViewBox(pg.ViewBox):
    drag_event = pyqtSignal(MouseDragEvent, QtCore.Qt.Modifier)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def mouseDragEvent(self, event):
        event.accept()
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        self.drag_event.emit(event, modifiers)
        if not modifiers in [QtCore.Qt.ShiftModifier,QtCore.Qt.ControlModifier]:
            pg.ViewBox.mouseDragEvent(self, event)

class ScatterPanel(QWidget):
    new_current_time = pyqtSignal(float)
    selection_change = pyqtSignal(list,list)

    def __init__(self, config, selected_intervals, 
                 data_path=None, name='', xlim=None, ylim=None, 
                 pointsize=20, linewidth=1, facecolor=(180,180,180), 
                 edgecolor=(100,100,100), selected_edgecolor=(255,255,0),
                 current_node_size=20, current_node_color=(255,0,0),
                 selection_intersection_threshold=0.5):

        super().__init__()
        assert data_path is not None
        self.selected_intervals = selected_intervals
        self.bounds = config['bounds']
        self.timestep = config['timestep']
        self.xlim = xlim
        self.ylim = ylim
        self.pointsize = pointsize
        self.linewidth = linewidth
        self.facecolor = facecolor
        self.edgecolor = edgecolor
        self.selected_edgecolor = selected_edgecolor
        self.current_node_size = current_node_size
        self.current_node_color = current_node_color
        self.selection_intersection_threshold = selection_intersection_threshold

        self.data = np.load(os.path.join(config['project_directory'],data_path))
        self.ncls = NCLS(*(self.data[:,2:]/self.timestep).astype(int).T, np.arange(self.data.shape[0]))

        self.viewBox = ScrubbableViewBox()
        self.plot = pg.PlotWidget(viewBox=self.viewBox)
        self.selection_rect = SelectionRectangle()
        self.scatter = pg.ScatterPlotItem()
        self.scatter_selected = pg.ScatterPlotItem()
        self.current_node_scatter = pg.ScatterPlotItem()
        self.scatter.sigClicked.connect(self.point_clicked)
        self.scatter_selected.sigClicked.connect(self.point_clicked)
        self.viewBox.drag_event.connect(self.drag_event)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.plot)

        self.current_node_brush = pg.mkBrush(color=self.current_node_color)
        self.current_node_scatter.setData(size=self.current_node_size, brush=self.current_node_brush)
        self.scatter.setData(pos=self.data[:,:2], data=np.arange(self.data.shape[0]), 
                             brush=pg.mkBrush(color=self.facecolor), size=self.pointsize, 
                             pen=pg.mkPen(color=self.edgecolor, width=self.linewidth))
        self.scatter_selected.setData(pos=self.data[:,:2], data=np.arange(self.data.shape[0]), 
                             brush=pg.mkBrush(color=self.facecolor), size=self.pointsize,
                             pen=pg.mkPen(color=self.selected_edgecolor, width=self.linewidth))
        self.scatter_selected.setPointsVisible(np.zeros(self.data.shape[0]))
        self.selection_rect.hide()
        self.plot.setClipToView(False)
        self.plot.addItem(self.scatter)
        self.plot.addItem(self.scatter_selected)
        self.plot.addItem(self.current_node_scatter)
        self.plot.addItem(self.selection_rect)
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        self.plot.setAspectLocked(True)

        xmin = self.data[:,0].min()
        xmax = self.data[:,0].max()
        ymin = self.data[:,1].min()
        ymax = self.data[:,1].max()
        xmin_padded = xmin - (xmax-xmin)*.02
        xmax_padded = xmax + (xmax-xmin)*.02
        ymin_padded = ymin - (ymax-ymin)*.02
        ymax_padded = ymax + (ymax-ymin)*.02
        #self.viewBox.setLimits(xMin=xmin_padded, xMax=xmax_padded, yMin=ymin_padded, yMax=ymax_padded)
        if self.xlim is not None: self.plot.setXRange(max(self.xlim[0],xmin_padded),min(self.xlim[1],xmax_padded))
        if self.ylim is not None: self.plot.setYRange(max(self.ylim[0],ymin_padded),min(self.ylim[1],ymax_padded))


    def update_current_time(self, t):
        use_t = np.array([t / self.timestep]).astype(int)
        current_nodes = self.ncls.all_containments_both(use_t,use_t+1,np.array([0]))[1]
        current_nodes_pos = self.data[current_nodes,:2]
        self.current_node_scatter.setData(pos=current_nodes_pos)


    def point_clicked(self, scatter, points):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if not modifiers in [QtCore.Qt.ShiftModifier, QtCore.Qt.ControlModifier]:
            index = points[0].index()
            new_time = self.data[index,2:].mean()
            self.new_current_time.emit(new_time)

    def drag_event(self, event, modifiers):
        position = self.viewBox.mapSceneToView(event.scenePos())
        position = np.array([position.x(), position.y()])
        if event.isFinish(): self.drag_end(position)
        elif modifiers in [QtCore.Qt.ShiftModifier, QtCore.Qt.ControlModifier]:
            if event.isStart(): self.drag_start(position)
            else: self.drag_move(position, modifiers)

    def drag_start(self, position):
        self.position_at_drag_start = position
        self.selection_rect.update_location(position, (0,0))
        self.selection_rect.show()

    def drag_move(self, position, modifiers):
        top_left = np.minimum(position, self.position_at_drag_start)
        bottom_right = np.maximum(position, self.position_at_drag_start)
        self.selection_rect.update_location(top_left, bottom_right-top_left)
        if modifiers == QtCore.Qt.ShiftModifier: selection_value = 1
        if modifiers == QtCore.Qt.ControlModifier: selection_value = 0
        enclosed_points = np.all([self.data[:,:2]>=top_left, self.data[:,:2]<=bottom_right],axis=0).all(1).nonzero()[0]
        self.selection_change.emit(list(self.data[enclosed_points,2:]), [selection_value]*len(enclosed_points))


    def update_selected_intervals(self):
        intersections = self.selected_intervals.intersection_proportions(self.data[:,2:])
        selected_points = intersections > self.selection_intersection_threshold
        self.scatter_selected.setPointsVisible(selected_points)

    def drag_end(self, position):
        self.selection_rect.hide()


class PanelStack(QWidget):
    def __init__(self, config, selected_intervals, **kwargs):
        super().__init__()
        self.panels = []
        self.selected_intervals = selected_intervals
        for scatter_props in config['scatters']: # initialize scatter plots
            scatter_panel = ScatterPanel(config, self.selected_intervals, **scatter_props)
            self.panels.append(scatter_panel)
            #scatter_panel.selection_change.connect(self.update_selection_mask)
            #scatter_panel.new_current_position.connect(self.update_current_position)
        for video_props in config['videos']: # initialize videos
            video_frame = VideoFrame(config, **video_props)
            self.panels.append(video_frame)
        self.initUI()

    def initUI(self):
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        self.setSizePolicy(sizePolicy)

        hbox = QHBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)
        for panel in self.panels:
            splitter.addWidget(panel)
        hbox.addWidget(splitter)
        hbox.setContentsMargins(5, 0, 10, 0)


    def update_current_time(self,t):
        for panel in self.panels:
            panel.update_current_time(t)

    def update_selected_intervals(self):
        for panel in self.panels: 
            panel.update_selected_intervals()



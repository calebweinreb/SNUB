from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pyqtgraph as pg
import numpy as np
import time
import os

from ncls import NCLS
from snub.gui.panels import Panel



class SelectionRectangle(pg.GraphicsObject):
    def __init__(self, topLeft=(0,0), size=(0,0)):
        pg.GraphicsObject.__init__(self)
        self.topLeft = topLeft
        self.size = size
        self.generatePicture()

    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        p.setBrush(pg.mkBrush((255,255,255,50)))
        tl = QPointF(self.topLeft[0], self.topLeft[1])
        size = QSizeF(self.size[0], self.size[1])
        p.drawRect(QRectF(tl, size))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def update_location(self, topLeft, size):
        self.topLeft = topLeft
        self.size = size
        self.generatePicture()

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())



class ScrubbableViewBox(pg.ViewBox):
    drag_event = pyqtSignal(object, Qt.Modifier)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def mouseDragEvent(self, event):
        event.accept()
        modifiers = QApplication.keyboardModifiers()
        self.drag_event.emit(event, modifiers)
        if not modifiers in [Qt.ShiftModifier,Qt.ControlModifier]:
            pg.ViewBox.mouseDragEvent(self, event)

class ScatterPanel(Panel):

    def __init__(self, config, selected_intervals, 
                 data_path=None, name='', xlim=None, ylim=None, 
                 pointsize=20, linewidth=1, facecolor=(180,180,180), 
                 edgecolor=(100,100,100), selected_edgecolor=(255,255,0),
                 current_node_size=20, current_node_color=(255,0,0),
                 selection_intersection_threshold=0.5, **kwargs):

        super().__init__(**kwargs)
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
        super().initUI()
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
        modifiers = QApplication.keyboardModifiers()
        if not modifiers in [Qt.ShiftModifier, Qt.ControlModifier]:
            index = points[0].index()
            new_time = self.data[index,2:].mean()
            self.new_current_time.emit(new_time)

    def drag_event(self, event, modifiers):
        position = self.viewBox.mapSceneToView(event.scenePos())
        position = np.array([position.x(), position.y()])
        if event.isFinish(): self.drag_end(position)
        elif modifiers in [Qt.ShiftModifier, Qt.ControlModifier]:
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
        if modifiers == Qt.ShiftModifier: selection_value = 1
        if modifiers == Qt.ControlModifier: selection_value = 0
        enclosed_points = np.all([self.data[:,:2]>=top_left, self.data[:,:2]<=bottom_right],axis=0).all(1).nonzero()[0]
        self.selection_change.emit(list(self.data[enclosed_points,2:]), [selection_value]*len(enclosed_points))


    def update_selected_intervals(self):
        intersections = self.selected_intervals.intersection_proportions(self.data[:,2:])
        selected_points = intersections > self.selection_intersection_threshold
        self.scatter_selected.setPointsVisible(selected_points)

    def drag_end(self, position):
        self.selection_rect.hide()

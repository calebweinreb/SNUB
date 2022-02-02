from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
import time
import os

from vidio import VideoReader
from snub.gui.utils import numpy_to_qpixmap
from snub.gui.panels import Panel

'''
Video code was borrowed and modified from 
https://github.com/jbohnslav/pose_annotator/blob/master/pose_annotator/gui/custom_widgets.py
'''

class VideoPanel(Panel):

    def __init__(self, config, video_path=None, timestamps_path=None, name='', **kwargs):
        super().__init__(**kwargs)
        self.video_frame = VideoFrame(os.path.join(config['project_directory'],video_path))
        self.timestamps = np.load(os.path.join(config['project_directory'],timestamps_path))
        self.update_current_time(config['current_time'])
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.video_frame)
        layout.setContentsMargins(0,0,0,0)
        self.video_frame.fitInView()
        self.video_frame.update()
        super().initUI()

    def update_current_time(self, t):
        i = min(self.timestamps.searchsorted(t), len(self.timestamps))
        self.video_frame.show_frame(i)



class VideoFrame(QGraphicsView):
    def __init__(self, video_path):
        super().__init__()
        self.vid = VideoReader(video_path)
        self.scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self.scene.addItem(self._photo)
        self.setScene(self.scene)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setSizePolicy(sizePolicy)
        self.grabGesture(Qt.PinchGesture)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setStyleSheet("background:transparent;")
        self.setMouseTracking(True)  
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def event(self, event):
        out = super().event(event)
        if type(event)==QGestureEvent:
            gesture = event.gesture(Qt.PinchGesture)
            scale = gesture.scaleFactor()
            self.scale(scale, scale)
        return out
        
    def fitInView(self, scale=True):
        rect = QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.scene.setSceneRect(rect)
            # if self.hasPhoto():
            unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
            self.scale(1 / unity.width(), 1 / unity.height())
            viewrect = self.viewport().rect()
            scenerect = self.transform().mapRect(rect)
            factor = min(viewrect.width() / scenerect.width(),
                         viewrect.height() / scenerect.height())
            self.scale(factor, factor)
            self._zoom = 0

    def show_frame(self, i):
        qpixmap = numpy_to_qpixmap(self.vid[i])
        # THIS LINE CHANGES THE SCENE WIDTH AND HEIGHT
        self._photo.setPixmap(qpixmap)
        self.update()


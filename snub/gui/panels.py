from PyQt5.QtCore import QDir, Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
import sys, os, cv2, json
import numpy as np
import cmapy
import time
import cv2
from vidio import VideoReader

'''
This code was borrowed and modified from 
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
    # print(type(qpixmap))
    return qpixmap


def float_to_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.float:
        image = (image * 255).clip(min=0, max=255).astype(np.uint8)
    # print(image)
    return image


class ClickableScene(QGraphicsScene):
    click = QtCore.pyqtSignal(QGraphicsSceneMouseEvent)
    move = QtCore.pyqtSignal(QGraphicsSceneMouseEvent)
    release = QtCore.pyqtSignal(QGraphicsSceneMouseEvent)
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def mousePressEvent(self, event):
        if event.buttons():
            self.click.emit(event)
            event.ignore()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.move.emit(event)
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.release.emit(event)
        super().mouseReleaseEvent(event)


class VideoFrame(QtWidgets.QGraphicsView):
     
    def __init__(self, project_directory=None, video_path=None, frame_index_path=None, name=""):
        assert project_directory is not None and video_path is not None
        super().__init__()
        self.initUI()
        self.name = name
        self.vid = VideoReader(os.path.join(project_directory,video_path))
        if frame_index_path is None: self.frame_index = np.arange(self.vid.nframes)
        else: self.frame_index = np.load(os.path.join(project_directory,frame_index_path))
        self.update_current_position(self.frame_index[0])
        self.fitInView()
        self.update()


    def initUI(self):  
        self.scene = ClickableScene(self) # QtWidgets.QGraphicsScene(self)
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

    def event(self, event):
        out = super(VideoFrame, self).event(event)
        if type(event)==QtWidgets.QGestureEvent:
            gesture = event.gesture(Qt.PinchGesture)
            scale = gesture.scaleFactor()
            last_scale = gesture.lastScaleFactor()
            self.scale(scale, last_scale)
        return out

    def update_current_position(self, value):
        value = int(np.clip(value, 0, len(self.frame_index)))
        self.frame = self.vid[value] # self.vid[self.frame_index[value]]
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
            # print(factor, viewrect, scenerect)
            self.scale(factor, factor)
            self._zoom = 0

    def adjust_aspect_ratio(self):
        if not hasattr(self, 'vid'):
            raise ValueError('Trying to set GraphicsView aspect ratio before video loaded.')
        if not hasattr(self.vid, 'width'):
            self.vid.width, self.vid.height = self.frame.shape[1], self.frame.shape[0]
        video_aspect = self.vid.width / self.vid.height
        H, W = self.height(), self.width()
        new_width = video_aspect * H
        if new_width < W:
            self.setFixedWidth(new_width)
        new_height = W / self.vid.width * self.vid.height
        if new_height < H:
            self.setFixedHeight(new_height)

    def show_image(self, array):
        qpixmap = numpy_to_qpixmap(array)
        # THIS LINE CHANGES THE SCENE WIDTH AND HEIGHT
        self._photo.setPixmap(qpixmap)
        self.update()

class PanelStack(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.panels = []
        
    def add_panel(self, panel):
        self.panels.append(panel)

    def initUI(self):
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        self.setSizePolicy(sizePolicy)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        for panel in self.panels:
            layout.addWidget(panel)

    def update_current_position(self,position):
        for panel in self.panels:
            panel.update_current_position(position)


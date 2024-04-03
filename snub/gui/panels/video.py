from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
import os

from vidio import VideoReader
from snub.gui.utils import HeaderMixin
from snub.gui.panels import Panel

"""
Video code was borrowed and modified from 
https://github.com/jbohnslav/pose_annotator/blob/master/pose_annotator/gui/custom_widgets.py
"""


def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    if isinstance(image.flat[0], np.floating):
        image = float_to_uint8(image)
    H, W, C = int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
    if C == 4:
        format = QImage.Format_RGBA8888
    elif C == 3:
        format = QImage.Format_RGB888
    else:
        raise ValueError("Aberrant number of channels: {}".format(C))
    qpixmap = QPixmap(QImage(image, W, H, image.strides[0], format))
    return qpixmap


class VideoPanel(Panel, HeaderMixin):
    def __init__(self, config, video_path=None, timestamps_path=None, **kwargs):
        super().__init__(config, **kwargs)
        self.video_frame = VideoFrame(video_path)
        self.timestamps = np.load(timestamps_path)
        self.current_frame_index = None
        self.is_visible = True
        self.update_current_time(config["init_current_time"])
        self.initUI(**kwargs)

    def initUI(self, **kwargs):
        super().initUI(**kwargs)
        self.layout.addWidget(self.video_frame)
        self.video_frame.fitInView()
        self.video_frame.update()

    def update_current_time(self, t):
        self.current_frame_index = min(
            self.timestamps.searchsorted(t), len(self.timestamps) - 1
        )
        if self.is_visible:
            self.video_frame.show_frame(self.current_frame_index)

    def toggle_visiblity(self, *args):
        super().toggle_visiblity(*args)
        if self.is_visible:
            self.video_frame.show_frame(self.current_frame_index)


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
        if type(event) == QGestureEvent:
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
            factor = min(
                viewrect.width() / scenerect.width(),
                viewrect.height() / scenerect.height(),
            )
            self.scale(factor, factor)
            self._zoom = 0

    def show_frame(self, i):
        qpixmap = numpy_to_qpixmap(self.vid[i])
        # THIS LINE CHANGES THE SCENE WIDTH AND HEIGHT
        self._photo.setPixmap(qpixmap)
        self.update()

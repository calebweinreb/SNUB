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

from snub.gui.video import VideoFrame
from snub.gui.tracks import TrackStack, Raster



def set_style(app):
    # https://www.wenzhaodesign.com/devblog/python-pyside2-simple-dark-theme
    # button from here https://github.com/persepolisdm/persepolis/blob/master/persepolis/gui/palettes.py
    app.setStyle(QStyleFactory.create("fusion"))

    darktheme = QtGui.QPalette()
    darktheme.setColor(QtGui.QPalette.Window, QtGui.QColor(45, 45, 45))
    darktheme.setColor(QtGui.QPalette.WindowText, QtGui.QColor(222, 222, 222))
    darktheme.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 45))
    darktheme.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(222, 222, 222))
    darktheme.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(222, 222, 222))
    # darktheme.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(0, 222, 0))
    darktheme.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(222, 222, 222))
    darktheme.setColor(QtGui.QPalette.Highlight, QtGui.QColor(45, 45, 45))
    darktheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Light, QtGui.QColor(60, 60, 60))
    darktheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Shadow, QtGui.QColor(50, 50, 50))
    darktheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText,
                       QtGui.QColor(111, 111, 111))
    darktheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, QtGui.QColor(122, 118, 113))
    darktheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText,
                       QtGui.QColor(122, 118, 113))
    darktheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Base, QtGui.QColor(32, 32, 32))
    app.setPalette(darktheme)
    return app
   
    

class MainWindow(QMainWindow):
    new_current_position = pyqtSignal(int)

    def __init__(self, fps=30):
        super(MainWindow, self).__init__()
        self.fps = fps
        self.playing = False
        self.current_position = 0
        
        # load config
        self.project_directory = sys.argv[1]+'/'
        config = json.load(open(self.project_directory+'config.json','r'))

        # video stack
        self.video_stack = []
        for video_props in config['videos']:
            self.video_stack.append(VideoFrame(project_directory=self.project_directory, **video_props))

        # create track stack
        self.trackStack = TrackStack(self, bounds=config['bounds'])
        for raster_props in config['rasters']:
            track = Raster(self.trackStack, project_directory=self.project_directory, **raster_props)
            self.trackStack.add_track(track)
        self.trackStack.initUI(vlines=config['vlines'])
        self.trackStack.new_current_position.connect(self.update_current_position)
        self.new_current_position.connect(self.trackStack.update_current_position)
        self.new_current_position.connect(self.update_current_position)

        # timer for video play
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.increment_position)

        # build layout
        self.initUI()


    def initUI(self):
        video_layout = QVBoxLayout()
        for video_frame in self.video_stack:
            video_layout.addWidget(video_frame)

        data_panels = QHBoxLayout()
        data_panels.addLayout(video_layout)
        data_panels.addWidget(self.trackStack)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_play_state)
        button_strip = QHBoxLayout()
        button_strip.addWidget(self.play_button)
        
        layout = QVBoxLayout()
        layout.addLayout(data_panels)
        layout.addLayout(button_strip)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def update_current_position(self,position):
        self.current_position = position
        for video_frame in self.video_stack:
            video_frame.update_frame(position)

    def increment_position(self):
        new_position = self.current_position + 1
        if new_position >= self.trackStack.bounds[1]:
            new_position = self.trackStack.bounds[0]
        self.new_current_position.emit(new_position)

    def toggle_play_state(self):
        if self.playing: self.pause()
        else: self.play()

    def play(self):
        self.timer.start(1000/self.fps)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.playing = True

    def pause(self):
        self.timer.stop()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playing = False

def run():
    app = QApplication(sys.argv)
    app = set_style(app)

    window = MainWindow()
    window.resize(1500, 768)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()





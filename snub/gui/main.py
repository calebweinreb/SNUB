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

from snub.gui.panels import PanelStack, VideoFrame, ScatterPanel
from snub.gui.tracks import TrackStack, Raster, Trace



def set_style(app):
    # https://www.wenzhaodesign.com/devblog/python-pyside2-simple-dark-theme
    # button from here https://github.com/persepolisdm/persepolis/blob/master/persepolis/gui/palettes.py
    app.setStyle(QStyleFactory.create("Fusion"))

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

def complete_config(config):
    if not 'fps' in config: config['fps'] = 30
    if not 'start_position' in config: config['start_position'] = 0
    if not 'scatters' in config: config['scatters'] = []
    if not 'rasters' in config: config['rasters'] = []
    if not 'videos' in config: config['videos'] = []
    return config
   
    

class ProjectTab(QWidget):
    new_current_position = pyqtSignal(int)

    def __init__(self, project_directory):
        super().__init__()
        self.playing = False
        
        # load config
        self.project_directory = project_directory
        config = json.load(open(os.path.join(self.project_directory,'config.json'),'r'))
        config = complete_config(config)
  
        self.bounds = config['bounds']
        self.fps = config['fps']
        self.current_position = config['start_position']
        self.selection_mask = np.zeros(self.bounds[1]-self.bounds[0])
        
        # create major gui elements
        self.panelStack = PanelStack()
        self.trackStack = TrackStack(bounds=self.bounds)

        # initialize scatter plots
        for scatter_props in config['scatters']:
            scatter_panel = ScatterPanel(project_directory=self.project_directory, bounds=self.bounds, **scatter_props)
            self.panelStack.add_panel(scatter_panel)
            scatter_panel.selection_change.connect(self.update_selection_mask)

        # initialize videos
        for video_props in config['videos']:
            video_frame = VideoFrame(project_directory=self.project_directory, **video_props)
            self.panelStack.add_panel(video_frame)
        

        # initialize rasters
        for raster_props in config['rasters']:
            track = Raster(self.trackStack, project_directory=self.project_directory, **raster_props)
            self.trackStack.add_track(track)
            if 'show_traces' in raster_props and raster_props['show_traces']==True:
                trace_track = Trace(self.trackStack, project_directory=self.project_directory, **raster_props)
                track.display_trace_signal.connect(trace_track.show_trace)
                track.has_trace_track = True
                self.trackStack.add_track(trace_track)

        # timer for live play
        self.timer = QTimer(self)

        # connect signals and slots
        self.trackStack.new_current_position.connect(self.update_current_position)
        self.trackStack.new_current_position.connect(self.panelStack.update_current_position)
        self.trackStack.selection_change.connect(self.update_selection_mask)
        self.new_current_position.connect(self.trackStack.update_current_position)
        self.new_current_position.connect(self.panelStack.update_current_position)
        self.new_current_position.connect(self.update_current_position)
        self.timer.timeout.connect(self.increment_position)

        # initialize layout
        self.trackStack.initUI(vlines=config['vlines'])
        self.panelStack.initUI()
        self.initUI()
        self.new_current_position.emit(self.current_position)



    def initUI(self):
        stacks = QHBoxLayout()
        stacks.addWidget(self.panelStack)
        stacks.addWidget(self.trackStack)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_play_state)
        self.deselect_button = QPushButton('Deselect All')
        self.deselect_button.clicked.connect(self.deselect_all)
        buttons = QHBoxLayout()
        buttons.addWidget(self.play_button)
        buttons.addWidget(self.deselect_button)

        layout = QVBoxLayout(self)
        layout.addLayout(stacks)
        layout.addLayout(buttons)


    def deselect_all(self):
        self.update_selection_mask([self.bounds], [0])

    def update_selection_mask(self, intervals, values):
        for interval,value in zip(intervals,values):
            shifted_interval = (int(interval[0]-self.bounds[0]), int(interval[1]-self.bounds[0]))
            shifted_interval = (max(shifted_interval[0],0), min(shifted_interval[1],len(self.selection_mask)-1))
            if interval[1] > interval[0]: self.selection_mask[shifted_interval[0]:shifted_interval[1]] = value 
        self.panelStack.update_selection_mask(self.selection_mask)
        self.trackStack.update_selection_mask(self.selection_mask)


        # if interval[0]-self.bounds[0] < 0: return
        # self.selection_mask[interval[0]-self.bounds[0]:interval[1]-self.bounds[0]] = value 
        # self.overlay.set_selection_intervals(self.selection_mask, self.bounds)
        # self.overlay.update()

    def update_current_position(self,position):
        self.current_position = position

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


class MainWindow(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)
        self.setWindowTitle('Systems Neuro Browser')

        open_project = QAction("&Open Project", self)
        open_project.setShortcut("Ctrl+O")
        open_project.setStatusTip('Open Project')
        open_project.triggered.connect(self.file_open)

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(open_project)

        for a in args:
            if os.path.exists(a): 
                self.open_project(a)


    def close_current_tab(self, i):
        # if there is only one tab do nothing
        if self.tabs.count() > 1: self.tabs.removeTab(i)

    def file_open(self):
        project_directory = QFileDialog.getExistingDirectory(self, 'Open Project')
        self.open_project(project_directory)

    def open_project(self, project_directory):
        name = project_directory.strip(os.path.sep).split(os.path.sep)[-1]
        project_tab = ProjectTab(project_directory)
        self.tabs.addTab(project_tab, name)
        self.tabs.setCurrentWidget(project_tab)


def run():
    app = QApplication(sys.argv)
    app = set_style(app)
    icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'assets','app_icon.png')
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow(sys.argv[1:])
    window.resize(1500, 900)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()





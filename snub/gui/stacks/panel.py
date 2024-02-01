from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from snub.gui.stacks import Stack
from snub.gui.panels import VideoPanel, ScatterPanel, ROIPanel, Pose3DPanel


class PanelStack(Stack):
    def __init__(self, config, selected_intervals):
        super().__init__(config, selected_intervals)
        self.size_ratio = config["panels_size_ratio"]

        for props in config["scatter"]:  # initialize scatter plots
            panel = ScatterPanel(config, self.selected_intervals, **props)
            self.widgets.append(panel)

        for props in config["video"]:  # initialize video
            panel = VideoPanel(config, **props)
            self.widgets.append(panel)

        for props in config["pose3D"]:  # initialize 3D pose viewer
            panel = Pose3DPanel(config, **props)
            self.widgets.append(panel)

        for props in config["roiplot"]:  # initialize ROI plot
            panel = ROIPanel(config, **props)
            self.widgets.append(panel)

        for w in self.widgets:
            w.closed.connect(self.widget_closed)

        self.initUI()

    def initUI(self):
        super().initUI()

        hbox = QHBoxLayout(self)
        self.splitter = QSplitter(Qt.Vertical)
        for panel in self.widgets:
            self.splitter.addWidget(panel)
        self.splitter.setSizes([w.size_ratio for w in self.widgets])

        hbox.addWidget(self.splitter)
        self.splitter.setSizes([100000 * p.size_ratio for p in self.widgets])
        hbox.setContentsMargins(0, 0, 0, 0)

    def get_by_name(self, name):
        for panel in self.widgets:
            if panel.name == name:
                return panel

    def update_current_time(self, t):
        for panel in self.widgets:
            panel.update_current_time(t)

    def update_selected_intervals(self):
        for panel in self.widgets:
            panel.update_selected_intervals()

    def change_layout_mode(self, layout_mode):
        self.splitter.setOrientation(
            {"columns": Qt.Vertical, "rows": Qt.Horizontal}[layout_mode]
        )
        super().change_layout_mode(layout_mode)

    def widget_closed(self):
        if not any([w.isVisible() for w in self.widgets]):
            self.hide()

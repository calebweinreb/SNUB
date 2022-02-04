from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np


class Stack(QWidget):
    def __init__(self, config, selected_intervals, **kwargs):
        super().__init__()
        self.widgets = []
        self.selected_intervals = selected_intervals

    def change_layout_mode(self, layout_mode):
        for widget in self.widgets: widget.change_layout_mode(layout_mode)
        

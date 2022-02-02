from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class Panel(QWidget):
    new_current_time = pyqtSignal(float)
    selection_change = pyqtSignal(list,list)

    def __init__(self, size_ratio=1, name='', **kwargs):
        super().__init__()
        self.size_ratio = size_ratio
        self.name = name

    def initUI(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_selected_intervals(self):
        pass

    def update_current_time(self, t):
        pass
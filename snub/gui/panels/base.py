from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from snub.gui.utils import HeaderMixin

class Panel(QWidget):
    new_current_time = pyqtSignal(float)
    selection_change = pyqtSignal(list,list)

    def __init__(self, config, size_ratio=1, **kwargs):
        super().__init__()
        self.size_ratio = size_ratio
        self.layout_mode = config['layout_mode']

    def update_selected_intervals(self):
        pass

    def update_current_time(self, t):
        pass

    def change_layout_mode(self, layout_mode):
        self.layout_mode = layout_mode
        if isinstance(self, HeaderMixin):
            self.save_current_size()
            self.update_layout()


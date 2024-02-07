from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


def _text_section(title, text):
    groupBox = QGroupBox()
    layout = QVBoxLayout()

    titleLabel = QLabel(title)
    titleLabel.setFont(QFont("Arial", 14, QFont.Bold))
    layout.addWidget(titleLabel)

    textlabel = QLabel(text)
    textlabel.setWordWrap(True)
    layout.addWidget(textlabel)
    layout.addStretch()

    groupBox.setLayout(layout)
    return groupBox


class HelpMenu:
    def __init__(self, parent):
        self.parent = parent
        self.helpMenu = QMenu("&Help", parent)
        self._setup_actions()

    def _setup_actions(self):
        action = QAction("Loading data", self.parent)
        action.triggered.connect(lambda: self._show_load_page())  # Correct connection
        self.helpMenu.addAction(action)

    def _show_load_page(self):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Loading data")
        dialog.setFixedWidth(600)
        dialogLayout = QVBoxLayout()
        dialog.setLayout(dialogLayout)

        subtitle = "Open a SNUB project"
        text = (
            "To open a SNUB project, go to File > Open Project, navigate to the project "
            'directory, and hit "Choose" with the directory selected. Multiple projects '
            "can be opened at once as different tabs. Projects can also be opened by including "
            "their paths as command line argument(s) when launching SNUB."
        )
        dialogLayout.addWidget(_text_section(subtitle, text))

        subtitle = "Reload a project"
        text = (
            "If a project is already open and its files have been modified outside of SNUB, "
            "the project can be reloaded in the SNUB GUI by going to File > Reload Project."
        )
        dialogLayout.addWidget(_text_section(subtitle, text))
        dialogLayout.addStretch()
        dialog.exec_()

    def get_menu(self):
        return self.helpMenu

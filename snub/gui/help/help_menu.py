from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import os
import markdown

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


class MarkdownDialog(QDialog):
    def __init__(self, markdown_text, parent=None):
        super(MarkdownDialog, self).__init__(parent)

        self.viewer = QTextBrowser(self)
        self.viewer.setReadOnly(True)

        html_text = markdown.markdown(markdown_text)
        self.viewer.setHtml(html_text)

        layout = QVBoxLayout(self)
        layout.addWidget(self.viewer)
        self.resize(900, 640)


class MarkdownViewer(QDialog):
    def __init__(self, markdown_file_path, parent=None):
        super().__init__(parent)
        self.initUI()
        self.loadMarkdownFile(markdown_file_path)

    def initUI(self):
        layout = QVBoxLayout(self)
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setOpenExternalLinks(False)  # Prevent opening external links
        self.textBrowser.anchorClicked.connect(
            self.handleLinkClicked
        )  # Handle internal links
        layout.addWidget(self.textBrowser)
        self.resize(900, 640)

    def loadMarkdownFile(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            markdown_content = file.read()
        html_content = markdown.markdown(markdown_content)
        self.textBrowser.setHtml(html_content)

    def handleLinkClicked(self, url):
        link = url.toString()
        if link.startswith("http"):
            QDesktopServices.openUrl(QUrl(link))
        else:
            self.loadMarkdownFile(os.path.join(CURRENT_DIR, link))


class HelpMenu:

    menu_pages = {
        "Loading data": "loading_data.md",
        "Timeline": "timeline.md",
        "Layout": "layout.md",
        "Heatmaps": "heatmaps.md",
        "Trace plots": "trace_plots.md",
        "Scatter plots": "scatter_plots.md",
        "Selections": "selections.md",
        "Video player": "video.md",
    }

    def __init__(self, parent):
        self.parent = parent
        self.helpMenu = QMenu("&Help", parent)
        self._setup_actions()

    def _setup_actions(self):
        for menu_text, page_name in self.menu_pages.items():
            action = QAction(menu_text, self.parent)
            action.triggered.connect(
                lambda _, mt=menu_text, pn=page_name: self._show_page(mt, pn)
            )
            self.helpMenu.addAction(action)
        self.helpMenu.addAction(action)

    def _show_page(self, menu_text, page_name):
        page_path = os.path.join(CURRENT_DIR, page_name)
        dialog = MarkdownViewer(page_path, self.parent)
        dialog.setWindowTitle(menu_text)
        dialog.exec_()

    def get_menu(self):
        return self.helpMenu

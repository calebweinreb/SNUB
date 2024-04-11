from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pyqtgraph as pg
import numpy as np
import pickle
import os

from snub.gui.tracks import Track, TrackGroup
from snub.io.project import _random_color
from snub.gui.utils import CHECKED_ICON_PATH, UNCHECKED_ICON_PATH


class CheckableComboBox(QComboBox):
    toggleSignal = pyqtSignal(bool, int)

    def __init__(self, width=100):
        super().__init__()
        self.setFixedWidth(width)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def addItem(self, label, color, checked=False):
        super().addItem(label)
        item_index = self.count() - 1
        item = self.model().item(item_index, 0)
        item.setFlags(Qt.ItemIsEnabled)
        item.setForeground(QColor("black"))
        item.setBackground(QColor(*color))
        if checked:
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        checked = item.checkState() == Qt.Checked
        self.toggleSignal.emit(not checked, index.row())

    def set_checked(self, index, checked):
        checkState = Qt.Checked if checked else Qt.Unchecked
        self.model().item(index, 0).setCheckState(checkState)


class TracePlot(Track):
    visible_traces_signal = pyqtSignal(set)

    def __init__(
        self,
        config,
        data_path=None,
        data=None,
        bound_rois="",
        initial_visible_traces=None,
        controls_padding_right=10,
        trace_colors={},
        linewidth=1,
        yaxis_width=30,
        controls_padding_top=5,
        trace_label_margin=4,
        **kwargs,
    ):
        super().__init__(config, **kwargs)
        self.controls_padding_right = controls_padding_right
        self.controls_padding_top = controls_padding_top
        self.trace_label_margin = trace_label_margin
        self.linewidth = linewidth
        self.bound_rois = None if len(bound_rois) == 0 else bound_rois

        self.auto_yaxis_limits = True
        self.yaxis_limits = (0, 1)
        self.adjust_yaxis_dialog = AdjustYaxisDialog(self)
        self.adjust_yaxis_dialog.new_axis_limits.connect(self.update_yaxis_limits)

        self.adjust_linewidth_dialog = AdjustLinewidthDialog(self, linewidth)
        self.adjust_linewidth_dialog.new_linewidth.connect(self.update_linewidth)

        if data is not None:
            self.data = data
        else:
            self.data = pickle.load(open(data_path, "rb"))

        if initial_visible_traces is not None:
            self.visible_traces = set(initial_visible_traces)
        elif len(self.data) > 0:
            self.visible_traces = set([np.random.choice(list(self.data.keys()))])
        else:
            self.visible_traces = set([])

        self.colors = dict(trace_colors)
        for label in self.data:
            if not label in self.colors:
                self.colors[label] = _random_color()

        self.dropDown = CheckableComboBox()
        self.dropDown.toggleSignal.connect(self.toggle_trace)

        self.plotWidget = pg.plot()
        self.plotWidget.hideAxis("bottom")
        self.plotWidget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.plotWidget.showGrid(x=False, y=True, alpha=0.5)
        self.plotWidget.getAxis("left").setWidth(yaxis_width)

        self.label_order = []
        self.trace_labels = []
        for label in self.data:
            self.dropDown.addItem(
                label, self.colors[label], checked=(label in self.visible_traces)
            )
            trace_label = QPushButton(label)
            trace_label.setFixedWidth(
                trace_label.fontMetrics().boundingRect(trace_label.text()).width() + 20
            )
            trace_label.setStyleSheet(
                "background-color: rgb(20,20,20); color: rgb({},{},{});".format(
                    *self.colors[label]
                )
            )
            trace_label.pressed.connect(self.trace_label_button_push)
            # trace_label.setMargin(self.trace_label_margin)
            if not label in self.visible_traces:
                trace_label.hide()
            self.label_order.append(label)
            self.trace_labels.append(trace_label)

        self.initUI()
        self.update_plot()

    def trace_label_button_push(self):
        self.hide_trace(self.sender().text())

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plotWidget)
        self.controls = QWidget(self)
        control_layout = QHBoxLayout(self.controls)
        control_layout.addStretch(0)
        for trace_label in self.trace_labels:
            control_layout.addWidget(trace_label, alignment=Qt.AlignTop)
        control_layout.addWidget(self.dropDown, alignment=Qt.AlignTop)
        self.update_controls_geometry()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(1, 1)
        self.update()

    def clear(self):
        for i in list(self.visible_traces):
            self.hide_trace(i, update_plot=False)
        self.update_plot()

    def toggle_trace(self, state, index):
        label = self.label_order[index]
        if state:
            self.show_trace(label)
        else:
            self.hide_trace(label)

    def show_trace(self, label, update_plot=True):
        if not label in self.visible_traces:
            index = self.label_order.index(label)
            self.dropDown.set_checked(index, True)
            self.visible_traces.add(label)
            self.trace_labels[index].show()
            if update_plot:
                self.update_plot()

    def hide_trace(self, label, update_plot=True):
        if label in self.visible_traces:
            index = self.label_order.index(label)
            self.dropDown.set_checked(index, False)
            self.visible_traces.remove(label)
            self.trace_labels[index].hide()
            if update_plot:
                self.update_plot()

    def update_plot(self):
        self.plotWidget.clear()
        for label in self.visible_traces:
            pen = pg.mkPen(QColor(*self.colors[label]), width=self.linewidth)
            self.plotWidget.plot(*self.data[label].T, pen=pen)
        if self.auto_yaxis_limits:
            self.plotWidget.enableAutoRange(axis=pg.ViewBox.YAxis)
        else:
            self.plotWidget.setYRange(*self.yaxis_limits, padding=0)

        self.visible_traces_signal.emit(self.visible_traces)

    def update_controls_geometry(self):
        self.controls.setGeometry(0, 0, self.width(), self.height())

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.update_Xrange()

    def update_Xrange(self):
        view_box_width = self.plotWidget.viewGeometry().width()
        yaxis_width = (
            (self.width() - view_box_width)
            / self.width()
            * (self.current_range[1] - self.current_range[0])
        )
        self.plotWidget.setXRange(
            self.current_range[0] + yaxis_width, self.current_range[1], padding=0
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_Xrange()
        self.update_controls_geometry()

    def bind_rois(self, roiplot):
        self.visible_traces_signal.connect(roiplot.update_visible_contours)
        self.visible_traces_signal.emit(self.visible_traces)

    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)

        def add_menu_item(name, slot, item_type="label"):
            action = QWidgetAction(self)
            if item_type == "checkbox":
                widget = QCheckBox(name)
                widget.stateChanged.connect(slot)
            elif item_type == "label":
                widget = QLabel(name)
                action.triggered.connect(slot)
            action.setDefaultWidget(widget)
            contextMenu.addAction(action)
            return widget

        checkbox = add_menu_item(
            "Automatic y-axis limits",
            self.toggle_auto_yaxis_limits,
            item_type="checkbox",
        )
        if self.auto_yaxis_limits:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)

        add_menu_item("Adjust y-axis limits", self.show_adjust_yaxis_dialog)
        contextMenu.addSeparator()

        add_menu_item("Adjust line width", self.show_adjust_linewidth_dialog)
        contextMenu.addSeparator()

        add_menu_item("Hide all traces", self.clear)

        contextMenu.setStyleSheet(
            f"""
            QMenu::item, QLabel, QCheckBox {{ background-color : #3e3e3e; padding: 5px 6px 5px 6px;}}
            QMenu::item:selected, QLabel:hover, QCheckBox:hover {{ background-color: #999999;}}
            QMenu::separator {{ background-color: rgb(20,20,20);}}
            QCheckBox::indicator:unchecked {{ image: url({UNCHECKED_ICON_PATH}); }}
            QCheckBox::indicator:checked {{ image: url({CHECKED_ICON_PATH}); }}
            QCheckBox::indicator {{ width: 14px; height: 14px;}}
            """
        )

        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

    def show_adjust_yaxis_dialog(self):
        if self.auto_yaxis_limits:
            self.yaxis_limits = self.plotWidget.getViewBox().viewRange()[1]
            self.adjust_yaxis_dialog.set_yaxis_limits(*self.yaxis_limits)
        self.adjust_yaxis_dialog.show()

    def show_adjust_linewidth_dialog(self):
        self.adjust_linewidth_dialog.show()

    def toggle_auto_yaxis_limits(self, state):
        self.auto_yaxis_limits = state
        if state:
            self.update_plot()

    def update_yaxis_limits(self, ymin, ymax):
        self.yaxis_limits = (ymin, ymax)
        self.auto_yaxis_limits = False
        self.update_plot()

    def update_linewidth(self, linewidth):
        self.linewidth = linewidth
        self.update_plot()


class AdjustYaxisDialog(QDialog):
    new_axis_limits = pyqtSignal(float, float)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.ymax = QLineEdit(self)
        self.ymin = QLineEdit(self)
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(lambda: self.hide())

        layout = QFormLayout(self)
        layout.addRow("Y-max", self.ymax)
        layout.addRow("Y-min", self.ymin)
        layout.addWidget(self.buttonBox)

    def accept(self):
        try:
            ymax, ymin = float(self.ymax.text()), float(self.ymin.text())
            self.new_axis_limits.emit(ymin, ymax)
            self.hide()
        except:
            pass

    def set_yaxis_limits(self, ymin, ymax):
        self.ymin.setText(str(ymin))
        self.ymax.setText(str(ymax))


class AdjustLinewidthDialog(QDialog):
    new_linewidth = pyqtSignal(int)

    def __init__(self, parent, linewidth):
        super().__init__(parent)
        self.parent = parent
        self.linewidth = QLineEdit(self)
        self.linewidth.setText(str(linewidth))
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(lambda: self.hide())

        layout = QFormLayout(self)
        layout.addRow("Line width", self.linewidth)
        layout.addWidget(self.buttonBox)

    def accept(self):
        try:
            linewidth = int(self.linewidth.text())
            assert linewidth > 0
            self.new_linewidth.emit(linewidth)
            self.hide()
        except:
            pass


class HeadedTracePlot(TrackGroup):
    def __init__(self, config, **kwargs):
        trace = TracePlot(config, **kwargs)
        super().__init__(
            config, tracks={"trace": trace}, track_order=["trace"], **kwargs
        )

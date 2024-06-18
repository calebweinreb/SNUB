from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
import json
from snub.gui.tracks import Track, TrackGroup, position_to_time
from snub.gui.utils import IntervalIndex, CHECKED_ICON_PATH, UNCHECKED_ICON_PATH


class AnnotatorLabels(QWidget):
    max_label_height = 20
    max_label_width = 300
    label_margin = 10

    def __init__(
        self,
        labels,
        label_color=(255, 255, 255),
        font_size=12,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.labels = labels
        self.label_color = label_color
        self.font_size = font_size

    def paintEvent(self, event):
        num_labels = len(self.labels)
        section_height = self.height() / num_labels

        self.resize(self.parent().size())
        qp = QPainter(self)

        # Draw row labels
        qp.setFont(QFont("Helvetica [Cronyx]", self.font_size))
        qp.setPen(QColor(*self.label_color))

        for ix, label in enumerate(self.labels):
            # Calculate the vertical position for the center of the current section
            y_center = (ix + 0.5) * section_height

            # Calculate the bounding rectangle of the text
            bounding_rect = qp.boundingRect(
                self.label_margin,
                0,
                self.max_label_width,
                self.max_label_height,
                Qt.AlignVCenter,
                label,
            )

            # Calculate the y position to center the text
            y_position = y_center - bounding_rect.height() / 2

            # Draw the text
            qp.drawText(
                self.label_margin,
                y_position,
                self.max_label_width,
                self.max_label_height,
                Qt.AlignVCenter,
                label,
            )

        # draw dividing lines between rows
        qp.setPen(QPen(QColor(*self.label_color), 2, Qt.SolidLine))
        for ix in range(num_labels + 1):
            y_position = int(ix * section_height)
            qp.drawLine(0, y_position, self.width(), y_position)


class Annotator(Track):

    def __init__(
        self,
        config,
        data_path=None,
        autosave=True,
        label_color=(255, 255, 255),
        off_color=(0, 0, 0),
        on_color=(255, 0, 0),
        label_font_size=12,
        **kwargs,
    ):
        super().__init__(config, **kwargs)
        with open(data_path, "r") as f:
            annotations = json.load(f)
        self.labels = sorted(annotations.keys())

        self.data_path = data_path
        self.off_color = off_color
        self.on_color = on_color
        self.autosave = autosave
        self.bounds = config["bounds"]

        self.drag_mode = 0  # +1 for shift-click, -1 for command-click
        self.drag_label_ix = None
        self.drag_initial_time = None

        self.label_widget = AnnotatorLabels(
            self.labels,
            label_color=label_color,
            font_size=label_font_size,
            parent=self,
        )

        self.annotation_intervals = []
        for k in self.labels:
            intervals = annotations[k]
            if len(intervals) > 0:
                index = IntervalIndex(intervals=np.array(intervals))
            else:
                index = IntervalIndex()
            self.annotation_intervals.append(index)

    def paintEvent(self, event):
        num_labels = len(self.labels)
        section_height = self.height() / num_labels
        qp = QPainter(self)

        # background color
        qp.fillRect(self.rect(), QColor(*self.off_color))

        # annotated intervals
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setPen(Qt.NoPen)
        qp.setBrush(QBrush(QColor(*self.on_color), Qt.SolidPattern))

        for ix in range(num_labels):
            y_low = section_height * ix
            y_high = section_height * (ix + 1)
            for s, e in self.annotation_intervals[ix].intervals:
                s_pos = int(self._time_to_position(s))
                e_pos = int(self._time_to_position(e))
                if e_pos > s_pos and e_pos > 0 and s_pos < self.width():
                    qp.drawRect(s_pos, y_low, e_pos - s_pos, y_high - y_low)

    def update_current_range(self, current_range):
        self.current_range = current_range

    def mouseMoveEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            t = self._position_to_time(event.x())
            self.drag_move(t, 1)
        elif modifiers == Qt.ControlModifier:
            t = self._position_to_time(event.x())
            self.drag_move(t, -1)
        else:
            super(Annotator, self).mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            t = self._position_to_time(event.x())
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ShiftModifier:
                t = self._position_to_time(event.x())
                ix = self._position_to_label_ix(event.y())
                self.drag_start(t, ix, 1)
            elif modifiers == Qt.ControlModifier:
                t = self._position_to_time(event.x())
                ix = self._position_to_label_ix(event.y())
                self.drag_start(t, ix, -1)
            else:
                super(Annotator, self).mouseMoveEvent(event)
        else:
            super(Annotator, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_end()
        super(Annotator, self).mouseMoveEvent(event)

    def drag_start(self, t, label_ix, mode):
        self.drag_mode = mode
        self.drag_initial_time = t
        self.drag_label_ix = label_ix

    def drag_end(self):
        self.drag_mode = 0
        self.drag_initial_time = None
        self.drag_label_ix = None
        if self.autosave:
            self.save_annotations()

    def drag_move(self, t, mode):
        if self.drag_mode == mode:
            s, e = sorted([self.drag_initial_time, t])
            if mode == 1:
                self.annotation_intervals[self.drag_label_ix].add_interval(s, e)
            elif mode == -1:
                self.annotation_intervals[self.drag_label_ix].remove_interval(s, e)
            self.update()

    def _position_to_label_ix(self, y):
        return int(y / self.height() * len(self.labels))

    def _position_to_time(self, p):
        t = position_to_time(self.current_range, self.width(), p)
        return np.clip(t, *self.bounds)

    def save_annotations(self, save_path=None):
        annotations = {}
        for ix, label in enumerate(self.labels):
            annotations[label] = self.annotation_intervals[ix].intervals.tolist()

        if save_path is None:
            save_path = self.data_path
        with open(save_path, "w") as f:
            json.dump(annotations, f)

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

        # toggle autosave
        checkbox = add_menu_item(
            "Automatically save",
            self.toggle_autosave,
            item_type="checkbox",
        )
        if self.autosave:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)

        # import/export annotations
        add_menu_item("Export annotations", self.export_annotations)
        add_menu_item("Import annotations", self.import_annotations)

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

    def toggle_autosave(self, state):
        self.autosave = state

    def export_annotations(self):
        pass

    def import_annotations(self):
        pass


class HeadedAnnotator(TrackGroup):
    def __init__(self, config, **kwargs):
        annotator = Annotator(config, **kwargs)
        super().__init__(
            config, tracks={"annotator": annotator}, track_order=["annotator"], **kwargs
        )

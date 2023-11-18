from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from functools import partial
import os
import numpy as np
import cmapy
import time
from numba import njit, prange

from snub.gui.tracks import Track, TracePlot, TrackGroup
from snub.gui.utils import AdjustColormapDialog
from snub.io.project import _random_color


def cvImage_to_Qimage(cvImage):
    height, width, channel = cvImage.shape
    bytesPerLine = 3 * width
    img_data = np.require(cvImage, np.uint8, "C")
    return QImage(img_data, width, height, bytesPerLine, QImage.Format_RGB888)


@njit
def map_heatmap_by_intervals(data, intervals, min_step):
    intervals = intervals - intervals[0, 0]
    num_cols = int(intervals[-1, 1] / min_step)
    output = np.zeros((data.shape[0], num_cols))
    for i in prange(intervals.shape[0]):
        start = int(intervals[i, 0] / min_step)
        end = int(intervals[i, 1] / min_step)
        output[:, start:end] = data[:, i : i + 1]
    return output


class HeatmapImage(Track):
    downsample_ratio = 3
    downsample_powers = 10
    max_display_resolution = 2000

    def __init__(
        self, config, image, start_time, binsize, vertical_range=None, parent=None
    ):
        super().__init__(config, parent=parent)
        self.binsize = binsize
        self.start_time = start_time
        self.downsample_options = self.downsample_ratio ** np.arange(
            self.downsample_powers
        )
        if vertical_range is None:
            self.vertical_range = [0, image.shape[0]]
        else:
            self.vertical_range = vertical_range
        self.set_image(image)

    def set_image(self, image_data):
        self.binned_images = [image_data]
        for i in range(self.downsample_powers):
            cols = image_data.shape[1] // self.downsample_ratio
            if cols > 0:
                image_data = (
                    image_data[:, : cols * self.downsample_ratio]
                    .reshape(image_data.shape[0], cols, -1, 3)
                    .mean(2)
                )
            self.binned_images.append(np.uint8(image_data))

    def get_current_pixmap(self):
        ### NOTE: CAN BE ABSTRACTED: SEE SIMILAR TIMELINE METHOD
        visible_bins = (self.current_range[1] - self.current_range[0]) / self.binsize
        downsample_ix = np.min(
            np.nonzero(
                visible_bins / self.downsample_options < self.max_display_resolution
            )[0]
        )
        use_image_data = self.binned_images[downsample_ix]
        use_image_data = use_image_data[self.vertical_range[0] : self.vertical_range[1]]
        use_range = [
            int(
                np.floor(
                    (self.current_range[0] - self.start_time)
                    / self.binsize
                    / self.downsample_options[downsample_ix]
                )
            ),
            int(
                np.ceil(
                    (self.current_range[1] - self.start_time)
                    / self.binsize
                    / self.downsample_options[downsample_ix]
                )
            ),
        ]
        if use_range[0] > use_image_data.shape[1] or use_range[1] < 0:
            use_image_data = np.zeros((50, 50, 3))
        elif use_range[0] >= 0 and use_range[1] <= use_image_data.shape[1]:
            use_image_data = use_image_data[:, use_range[0] : use_range[1]]
        elif use_range[0] >= 0 and use_range[1] > use_image_data.shape[1]:
            use_image_data = np.pad(
                use_image_data[:, use_range[0] :],
                ((0, 0), (0, use_range[1] - use_image_data.shape[1]), (0, 0)),
            )
        elif use_range[0] < 0 and use_range[1] <= use_image_data.shape[1]:
            use_image_data = np.pad(
                use_image_data[:, : use_range[1]], ((0, 0), (-use_range[0], 0), (0, 0))
            )
        return QPixmap(cvImage_to_Qimage(use_image_data.astype(np.uint8)))

    def paintEvent(self, event):
        self.resize(self.parent().size())
        qp = QPainter(self)
        pixmap = self.get_current_pixmap().scaled(self.size())
        qp.setRenderHint(QPainter.Antialiasing)
        qp.drawPixmap(QPoint(0, 0), pixmap)

    def update_vertical_range(self, vrange):
        self.vertical_range = vrange
        self.update()


class HeatmapLabels(QWidget):
    display_trace_signal = pyqtSignal(str)
    max_label_height = 20
    label_margin = 10

    def __init__(
        self,
        labels,
        label_order=None,
        label_colors=None,
        max_label_width=300,
        base_alpha=80,
        highlighted_alpha=255,
        base_font_size=10,
        highlighted_font_size=20,
        vertical_range=None,
        parent=None,
    ):
        super().__init__(parent=parent)

        self.labels = labels
        self.label_colors = label_colors
        if label_order is not None:
            self.label_order = label_order
        else:
            self.label_order = np.arange(len(labels))

        self.max_label_width = max_label_width
        if vertical_range is None:
            vertical_range = [0, len(labels)]
        else:
            self.vertical_range = vertical_range

        self.base_alpha = base_alpha
        self.base_font_size = base_font_size
        self.highlighted_alpha = highlighted_alpha
        self.highlighted_font_size = highlighted_font_size
        self.highlighted_labels = set([])

        qm = QFontMetrics(QFont("Helvetica [Cronyx]", self.base_font_size))
        self.label_widths = [qm.width(l) + self.label_margin * 2 for l in labels]
        self.setMouseTracking(True)
        self.hover_label = None

    def update_label_order(self, label_order):
        self.label_order = label_order
        self.update()

    def update_vertical_range(self, vrange):
        self.vertical_range = vrange
        self.update()

    def highlight_labels(self, labels):
        self.highlighted_labels = set(labels)
        self.update()

    def label_at_position(self, x, y):
        height_abs = (
            y / self.height() * (self.vertical_range[1] - self.vertical_range[0])
            + self.vertical_range[0]
        )
        i = self.label_order[
            int(np.clip(height_abs + 0.5, 0, len(self.label_order) - 1))
        ]
        if x < self.label_widths[i]:
            return self.labels[i]

    def mouseMoveEvent(self, event):
        self.hover_label = self.label_at_position(event.x(), event.y())
        self.update()
        event.ignore()

    def mousePressEvent(self, event):
        label = self.label_at_position(event.x(), event.y())
        if label is not None:
            self.display_trace_signal.emit(label)
        else:
            event.ignore()

    def paintEvent(self, event):
        self.resize(self.parent().size())
        qp = QPainter()
        qp.begin(self)
        for height, i in enumerate(self.label_order):
            height = (height + 0.5 - self.vertical_range[0]) / (
                self.vertical_range[1] - self.vertical_range[0]
            )
            if height > 0 and height < 1:
                if (
                    self.labels[i] in self.highlighted_labels
                    or self.labels[i] == self.hover_label
                ):
                    qp.setFont(
                        QFont(
                            "Helvetica [Cronyx]", self.highlighted_font_size, QFont.Bold
                        )
                    )
                    qp.setPen(QColor(*self.label_colors[i], self.highlighted_alpha))
                else:
                    qp.setFont(QFont("Helvetica [Cronyx]", self.base_font_size))
                    qp.setPen(QColor(*self.label_colors[i], self.base_alpha))
                qp.drawText(
                    self.label_margin,
                    height * self.height() - self.max_label_height // 2,
                    self.max_label_width,
                    self.max_label_height,
                    Qt.AlignVCenter,
                    self.labels[i],
                )
        qp.end()


class Heatmap(Track):
    display_trace_signal = pyqtSignal(str)

    def __init__(
        self,
        config,
        selected_intervals,
        row_colors=None,
        labels_path=None,
        data_path=None,
        intervals_path=None,
        colormap="viridis",
        max_label_width=300,
        row_order_path=None,
        initial_show_labels=True,
        label_color=(255, 255, 255),
        label_font_size=12,
        vmin=0,
        vmax=1,
        add_traceplot=False,
        vertical_range=None,
        **kwargs
    ):
        super().__init__(config, **kwargs)
        self.selected_intervals = selected_intervals
        self.vmin, self.vmax = vmin, vmax
        self.colormap = colormap
        self.add_traceplot = add_traceplot
        self.min_step = config["min_step"]

        self.data = np.load(os.path.join(config["project_directory"], data_path))
        self.intervals = np.load(
            os.path.join(config["project_directory"], intervals_path)
        )

        if labels_path is None:
            self.labels = [str(i) for i in range(self.data.shape[0])]
        else:
            self.labels = (
                open(os.path.join(config["project_directory"], labels_path), "r")
                .read()
                .split("\n")
            )

        if row_colors is None:
            row_colors = [_random_color() for i in range(self.data.shape[0])]
        self.row_colors = row_colors

        if row_order_path is None:
            self.row_order = np.arange(self.data.shape[0])
        else:
            self.row_order = np.load(
                os.path.join(config["project_directory"], row_order_path)
            )
        self.initial_row_order = self.row_order.copy()

        if vertical_range is None:
            self.vertical_range = [0, self.data.shape[0]]
        else:
            self.vertical_range = vertical_range

        self.adjust_colormap_dialog = AdjustColormapDialog(self, self.vmin, self.vmax)
        self.adjust_colormap_dialog.new_range.connect(self.update_colormap_range)

        self.heatmap_image = HeatmapImage(
            config,
            image=self.get_image_data(),
            start_time=self.intervals[0, 0],
            binsize=self.min_step,
            vertical_range=self.vertical_range,
            parent=self,
        )

        self.heatmap_labels = HeatmapLabels(
            self.labels,
            label_order=self.row_order,
            label_colors=row_colors,
            vertical_range=self.vertical_range,
            max_label_width=max_label_width,
            parent=self,
        )
        if not initial_show_labels:
            self.heatmap_labels.hide()

    def update_current_range(self, current_range):
        self.current_range = current_range
        self.heatmap_image.update_current_range(current_range)

    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)

        def add_menu_item(name, slot, item_type="label"):
            action = QWidgetAction(self)
            if item_type == "checkbox":
                widget = QCheckBox(name)
                widget.stateChanged.connect(slot)
            elif item_type == "button":
                widget = QPushButton(name)
                widget.clicked.connect(slot)
            elif item_type == "label":
                widget = QLabel(name)
                action.triggered.connect(slot)
            else:
                return
            action.setDefaultWidget(widget)
            contextMenu.addAction(action)
            return widget

        # used to get row label and for zooming
        y = (
            event.y()
            / self.height()
            * (self.vertical_range[1] - self.vertical_range[0])
            + self.vertical_range[0]
        )

        # if there's an associated traceplot, offer to plot clicked row
        if self.add_traceplot:
            row_label = self.labels[self.row_order[int(y)]]
            display_trace_slot = lambda: self.display_trace_signal.emit(row_label)
            add_menu_item("Plot trace: {}".format(row_label), display_trace_slot)

        # show adjust colormap dialog
        add_menu_item("Adjust colormap range", self.show_adjust_colormap_dialog)
        contextMenu.addSeparator()

        if self.heatmap_labels.isVisible():
            add_menu_item("Hide row labels", self.hide_labels)
        else:
            add_menu_item("Show row labels", self.show_labels)
        contextMenu.addSeparator()

        # for reordering rows
        add_menu_item("Reorder by selection", self.reorder_by_selection)
        add_menu_item("Restore original order", self.restore_original_order)
        contextMenu.addSeparator()

        # for changing vertical range
        add_menu_item(
            "Zoom in (vertical)",
            partial(self.zoom_vertical, y, 2 / 3),
            item_type="button",
        )
        add_menu_item(
            "Zoom out (vertical)",
            partial(self.zoom_vertical, y, 3 / 2),
            item_type="button",
        )

        contextMenu.setStyleSheet(
            """
            QLabel, QPushButton { background-color : #3E3E3E; padding: 10px 12px 10px 12px;}
            QLabel:hover, QPushButton:hover { background-color: #999999;} 
            QMenu::separator { background-color: rgb(20,20,20);} """
        )
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

    def show_labels(self):
        self.heatmap_labels.show()

    def hide_labels(self):
        self.heatmap_labels.hide()

    def reorder_by_selection(self):
        weights = self.selected_intervals.intersection_proportions(self.intervals)
        activation = (self.data * weights).sum(1)
        self.update_row_order(np.argsort(activation)[::-1])

    def restore_original_order(self):
        self.update_row_order(self.initial_row_order)

    def update_row_order(self, order):
        self.row_order = order
        self.update_image_data()
        self.heatmap_labels.update_label_order(order)

    def update_image_data(self):
        image_data = self.get_image_data()
        self.heatmap_image.set_image(image_data)

    def get_image_data(self):
        data_remapped = map_heatmap_by_intervals(
            self.data, self.intervals, self.min_step
        )
        data_scaled = (
            np.clip(
                (data_remapped[self.row_order] - self.vmin) / (self.vmax - self.vmin),
                0,
                1,
            )
            * 255
        )
        image_data = cmapy.cmap(self.colormap).squeeze()[:, ::-1][
            data_scaled.astype(np.uint8)
        ]
        return image_data

    def update_colormap_range(self, vmin, vmax):
        self.vmin, self.vmax = vmin, vmax
        self.update_image_data()

    def show_adjust_colormap_dialog(self):
        self.adjust_colormap_dialog.show()

    def zoom_vertical(self, origin, scale_factor):
        scale_change = max(
            scale_factor, 1 / (self.vertical_range[1] - self.vertical_range[0])
        )
        new_vrange = [
            int(
                max(
                    np.floor((self.vertical_range[0] - origin) * scale_change + origin),
                    0,
                )
            ),
            int(
                min(
                    np.ceil((self.vertical_range[1] - origin) * scale_change + origin),
                    self.data.shape[0],
                )
            ),
        ]
        self.vertical_range = new_vrange
        self.heatmap_image.update_vertical_range(self.vertical_range)
        self.heatmap_labels.update_vertical_range(self.vertical_range)


class HeadedHeatmap(TrackGroup):
    def __init__(self, config, selected_intervals, **kwargs):
        heatmap = Heatmap(config, selected_intervals, **kwargs)
        super().__init__(
            config, tracks={"heatmap": heatmap}, track_order=["heatmap"], **kwargs
        )


class HeatmapTraceGroup(TrackGroup):
    def __init__(
        self,
        config,
        selected_intervals,
        trace_height_ratio=1,
        bound_rois="",
        heatmap_height_ratio=2,
        height_ratio=1,
        row_colors=None,
        **kwargs
    ):
        heatmap = Heatmap(
            config,
            selected_intervals,
            row_colors=row_colors,
            height_ratio=heatmap_height_ratio,
            **kwargs
        )

        ts = heatmap.intervals.mean(1)
        trace = TracePlot(
            config,
            height_ratio=trace_height_ratio,
            bound_rois=bound_rois,
            data={
                l: np.vstack((ts, d)).T for l, d in zip(heatmap.labels, heatmap.data)
            },
            colors={l: c for l, c in zip(heatmap.labels, heatmap.row_colors)},
            **kwargs
        )

        heatmap.display_trace_signal.connect(trace.show_trace)
        heatmap.heatmap_labels.display_trace_signal.connect(trace.show_trace)
        trace.visible_traces_signal.connect(heatmap.heatmap_labels.highlight_labels)
        trace.visible_traces_signal.emit(trace.visible_traces)

        super().__init__(
            config,
            tracks={"trace": trace, "heatmap": heatmap},
            track_order=["trace", "heatmap"],
            height_ratio=height_ratio,
            **kwargs
        )

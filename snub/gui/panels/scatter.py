from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
import os
import cmapy
from functools import partial

from vispy.scene import SceneCanvas
from vispy.scene.visuals import Markers, Rectangle
from vispy.util import keys

from snub.gui.panels import Panel
from snub.gui.utils import HeaderMixin, AdjustColormapDialog, IntervalIndex


class ScatterPanel(Panel, HeaderMixin):
    eps = 1e-10

    def __init__(
        self,
        config,
        selected_intervals,
        data_path=None,
        name="",
        pointsize=10,
        linewidth=1,
        facecolor=(180, 180, 180),
        xlim=None,
        ylim=None,
        selected_edgecolor=(255, 255, 0),
        edgecolor=(0, 0, 0),
        current_node_size=20,
        current_node_color=(255, 0, 0),
        colormap="viridis",
        selection_intersection_threshold=0.5,
        variable_labels=[],
        **kwargs
    ):
        super().__init__(config, **kwargs)
        assert data_path is not None
        self.selected_intervals = selected_intervals
        self.bounds = config["bounds"]
        self.min_step = config["min_step"]
        self.pointsize = pointsize
        self.linewidth = linewidth
        self.facecolor = np.array(facecolor) / 256
        self.edgecolor = np.array(edgecolor) / 256
        self.colormap = colormap
        self.selected_edgecolor = np.array(selected_edgecolor) / 256
        self.current_node_size = current_node_size
        self.current_node_color = np.array(current_node_color) / 256
        self.selection_intersection_threshold = selection_intersection_threshold
        self.variable_labels = ["Interval start", "Interval end"] + variable_labels
        self.vmin, self.vmax = 0, 1
        self.current_variable_label = "(No color)"
        self.sort_nodes_by_variable = True
        self.show_marker_trail = False

        self.data = np.load(os.path.join(config["project_directory"], data_path))
        self.data[:, 2:4] = self.data[:, 2:4] + np.array([-self.eps, self.eps])
        self.is_selected = np.zeros(self.data.shape[0]) > 0
        self.plot_order = np.arange(self.data.shape[0])
        self.interval_index = IntervalIndex(
            min_step=self.min_step, intervals=self.data[:, 2:4]
        )
        self.adjust_colormap_dialog = AdjustColormapDialog(self, self.vmin, self.vmax)
        self.variable_menu = QListWidget(self)
        self.variable_menu.itemClicked.connect(self.variable_menu_item_clicked)
        self.show_variable_menu()

        self.canvas = SceneCanvas(self, keys="interactive", show=True)
        self.canvas.events.mouse_move.connect(self.mouse_move)
        self.canvas.events.mouse_release.connect(self.mouse_release)
        self.viewbox = self.canvas.central_widget.add_grid().add_view(
            row=0, col=0, camera="panzoom"
        )
        self.viewbox.camera.aspect = 1
        self.scatter = Markers(antialias=0)
        self.scatter_selected = Markers(antialias=0)
        self.current_node_marker = Markers(antialias=0)
        self.rect = Rectangle(
            border_color=(1, 1, 1),
            color=(1, 1, 1, 0.2),
            center=(0, 0),
            width=1,
            height=1,
        )
        self.viewbox.add(self.scatter)
        self.initUI(
            name=name,
            xlim=xlim,
            ylim=ylim,
        )

    def initUI(self, xlim=None, ylim=None, **kwargs):
        super().initUI(**kwargs)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.variable_menu)
        splitter.addWidget(self.canvas.native)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 3)
        self.layout.addWidget(splitter)
        self.update_scatter()
        if xlim is None:
            xlim = [self.data[:, 0].min(), self.data[:, 0].max()]
        if ylim is None:
            ylim = [self.data[:, 1].min(), self.data[:, 1].max()]
        self.viewbox.camera.set_range(x=xlim, y=ylim, margin=0.1)
        self.rect.order = 0
        self.current_node_marker.order = 1
        self.scatter_selected.order = 2
        self.scatter.order = 3
        self.variable_menu.setStyleSheet(
            """
            QListWidget::item { background-color : #3E3E3E; color:white; padding: 5px 6px 5px 6px;}
            QListWidget::item:hover, QLabel:hover { background-color: #999999; color:white; } 
            QListWidget { background-color : #3E3E3E; }"""
        )

    def update_scatter(self):
        if self.current_variable_label in self.variable_labels:
            x = self.data[
                :, 2 + self.variable_labels.index(self.current_variable_label)
            ]
            if self.sort_nodes_by_variable:
                self.plot_order = np.argsort(x)[::-1]
            else:
                self.plot_order = np.arange(len(x))
            x = np.clip((x - self.vmin) / (self.vmax - self.vmin), 0, 1)[
                self.plot_order
            ]
            face_color = (
                cmapy.cmap(self.colormap).squeeze()[:, ::-1][(255 * x).astype(int)]
                / 255
            )
        else:
            face_color = np.repeat(self.facecolor[None], self.data.shape[0], axis=0)

        self.scatter.set_data(
            pos=self.data[self.plot_order, :2],
            face_color=face_color,
            edge_color=self.edgecolor,
            edge_width=self.linewidth,
            size=self.pointsize,
        )

        if self.is_selected.any():
            is_selected = self.is_selected[self.plot_order]
            self.scatter_selected.set_data(
                pos=self.data[self.plot_order, :2][is_selected],
                face_color=face_color[is_selected],
                edge_color=self.selected_edgecolor,
                edge_width=(self.linewidth * 2),
                size=self.pointsize,
            )
            self.scatter_selected.parent = self.viewbox.scene
        else:
            self.scatter_selected.parent = None

    def update_current_time(self, t):
        if self.show_marker_trail:
            times = np.linspace(t, t - 5, 11)
            sizes = np.exp(np.linspace(0, -1.5, 11))
        else:
            times = np.array([t])
            sizes = np.array([1])
        nodes, time_indexes = self.interval_index.intervals_containing(times)
        if len(nodes) > 0:
            self.current_node_marker.set_data(
                pos=self.data[nodes, :2],
                face_color=self.current_node_color,
                size=sizes[time_indexes] * self.current_node_size,
            )
            self.current_node_marker.parent = self.viewbox.scene
        else:
            self.current_node_marker.parent = None

    def context_menu(self, event):
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

        # show/hide variable menu
        if self.variable_menu.isVisible():
            add_menu_item("Hide variables menu", self.hide_variable_menu)
        else:
            add_menu_item("Show variables menu", self.show_variable_menu)

        # get enriched variables (only available is nodes are selected)
        label = add_menu_item(
            "Sort variables by enrichment", self.get_enriched_variables
        )
        if self.is_selected.sum() == 0:
            label.setStyleSheet("QLabel { color: rgb(120,120,120); }")
        label = add_menu_item(
            "Restore original variable order", self.show_variable_menu
        )
        contextMenu.addSeparator()

        # toggle whether to plot high-variable-val nodes on top
        checkbox = add_menu_item(
            "Plot high values on top",
            self.toggle_sort_by_color_value,
            item_type="checkbox",
        )
        if self.sort_nodes_by_variable:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)
        contextMenu.addSeparator()

        # click to show adjust colormap range dialog
        label = add_menu_item("Adjust colormap range", self.show_adjust_colormap_dialog)
        contextMenu.addSeparator()

        if self.show_marker_trail:
            add_menu_item("Hide marker trail", partial(self.toggle_marker_trail, False))
        else:
            add_menu_item("Show marker trail", partial(self.toggle_marker_trail, True))

        contextMenu.setStyleSheet(
            """
            QMenu::item, QLabel, QCheckBox { background-color : #3E3E3E; padding: 5px 6px 5px 6px;}
            QMenu::item:selected, QLabel:hover, QCheckBox:hover { background-color: #999999;}
            QMenu::separator { background-color: rgb(20,20,20);} """
        )
        action = contextMenu.exec_(event.native.globalPos())

    def toggle_marker_trail(self, visibility):
        self.show_marker_trail = visibility
        self.update_scatter()

    def variable_menu_item_clicked(self, item):
        self.colorby(item.text())

    def hide_variable_menu(self):
        self.variable_menu.hide()

    def show_variable_menu(self, *args, variable_order=None):
        self.variable_menu.clear()
        if variable_order is None:
            variable_order = self.variable_labels
        for name in variable_order:
            self.variable_menu.addItem(name)
        self.variable_menu.show()

    def get_enriched_variables(self):
        if self.is_selected.sum() > 0 and len(self.variable_labels) > 0:
            variables_zscore = (self.data[:, 2:] - self.data[:, 2:].mean(0)) / (
                np.std(self.data[:, 2:], axis=0) + self.eps
            )
            enrichment = variables_zscore[self.is_selected].mean(0)
            variable_order = [self.variable_labels[i] for i in np.argsort(-enrichment)]
            self.show_variable_menu(variable_order=variable_order)

    def update_colormap_range(self, vmin, vmax):
        self.vmin, self.vmax = vmin, vmax
        self.update_scatter()

    def toggle_sort_by_color_value(self, check_state):
        if check_state == 0:
            self.sort_nodes_by_variable = False
        else:
            self.sort_nodes_by_variable = True
        self.update_scatter()

    def show_adjust_colormap_dialog(self):
        self.adjust_colormap_dialog.show()

    def colorby(self, label):
        self.current_variable_label = label
        if self.current_variable_label in self.variable_labels:
            x = self.data[
                :, 2 + self.variable_labels.index(self.current_variable_label)
            ]
            self.vmin, self.vmax = x.min() - self.eps, x.max() + self.eps
            self.adjust_colormap_dialog.update_range(self.vmin, self.vmax)
        self.update_scatter()

    def mouse_release(self, event):
        self.rect.parent = None
        if event.button == 2:
            self.context_menu(event)

    def mouse_move(self, event):
        if event.is_dragging:
            mods = event.modifiers
            if keys.SHIFT in mods or keys.CONTROL in mods:
                current_pos = self.viewbox.scene.transform.imap(event.pos)[:2]
                start_pos = self.viewbox.scene.transform.imap(event.press_event.pos)[:2]
                if all((current_pos - start_pos) != 0):
                    self.rect.center = (current_pos + start_pos) / 2
                    self.rect.width = np.abs(current_pos[0] - start_pos[0])
                    self.rect.height = np.abs(current_pos[1] - start_pos[1])
                    self.rect.parent = self.viewbox.scene

                selection_value = int(mods[0] == keys.SHIFT)
                enclosed_points = np.all(
                    [
                        self.data[:, :2] >= np.minimum(current_pos, start_pos),
                        self.data[:, :2] <= np.maximum(current_pos, start_pos),
                    ],
                    axis=(0, 2),
                )
                self.selection_change.emit(
                    list(self.data[enclosed_points, 2:4]),
                    [selection_value] * len(enclosed_points),
                )

    def update_selected_intervals(self):
        intersections = self.selected_intervals.intersection_proportions(
            self.data[:, 2:4]
        )
        self.is_selected = intersections > self.selection_intersection_threshold
        self.update_scatter()

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
import os
import cv2
from scipy.sparse import load_npz
from vidio import VideoReader

from vispy.scene import SceneCanvas
from vispy.scene.visuals import Image, Line

from snub.gui.panels import Panel
from snub.gui.utils import HeaderMixin, AdjustColormapDialog
from snub.io.project import _random_color


def _roi_contours(rois, dims, threshold_max_ratio=0.2, blur_kernel=2):
    rois = np.array(rois.todense()).reshape(rois.shape[0], *dims)
    contour_coordinates = []
    for roi in rois:
        roi_blur = cv2.GaussianBlur(roi, (11, 11), blur_kernel)
        roi_mask = roi_blur > roi_blur.max() * threshold_max_ratio
        xy = cv2.findContours(
            roi_mask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )[0][0].squeeze()
        contour_coordinates.append(np.vstack((xy, xy[:1])))
    return contour_coordinates


class ROIPanel(Panel, HeaderMixin):
    eps = 1e-10

    def __init__(
        self,
        config,
        rois_path=None,
        labels_path=None,
        timestamps_path=None,
        dimensions=None,
        video_paths=None,
        contour_colors={},
        linewidth=3,
        initial_selected_rois=[],
        vmin=0,
        vmax=1,
        colormap="viridis",
        **kwargs
    ):
        super().__init__(config, **kwargs)

        self.linewidth = linewidth
        self.colormap = colormap
        self.vmin, self.vmax = vmin, vmax
        self.dims = dimensions
        self.current_frame_index = None
        self.is_visible = True

        self.rois = load_npz(os.path.join(config["project_directory"], rois_path))
        self.timestamps = np.load(
            os.path.join(config["project_directory"], timestamps_path)
        )

        if labels_path is None:
            self.labels = [str(i) for i in range(self.rois.shape[0])]
        else:
            self.labels = (
                open(os.path.join(config["project_directory"], labels_path), "r")
                .read()
                .split("\n")
            )

        self.adjust_colormap_dialog = AdjustColormapDialog(self, self.vmin, self.vmax)
        self.adjust_colormap_dialog.new_range.connect(self.update_colormap_range)

        self.canvas = SceneCanvas(self, keys="interactive", show=True)
        self.canvas.events.mouse_release.connect(self.mouse_release)
        self.viewbox = self.canvas.central_widget.add_grid().add_view(
            row=0, col=0, camera="panzoom"
        )
        self.viewbox.camera.set_range(
            x=(0, self.dims[1]), y=(0, self.dims[0]), margin=0
        )
        self.viewbox.camera.aspect = 1

        self.contours = {}
        for label, coordinates in zip(self.labels, _roi_contours(self.rois, self.dims)):
            color = (
                contour_colors[label] if label in contour_colors else _random_color()
            )
            self.contours[label] = Line(
                coordinates,
                color=np.array(color) / 255,
                width=self.linewidth,
                connect="strip",
                parent=None,
            )

        self.vids = {
            name: VideoReader(os.path.join(config["project_directory"], video_path))
            for name, video_path in video_paths.items()
        }

        self.dropDown = QComboBox()
        self.dropDown.addItems(list(video_paths.keys())[::-1])
        self.dropDown.activated.connect(self.update_image)

        self.image = Image(
            np.zeros(self.dims, dtype=np.float32),
            cmap=colormap,
            parent=self.viewbox.scene,
            clim=(0, 1),
        )
        self.update_current_time(config["init_current_time"])
        self.initUI(**kwargs)

    def initUI(self, **kwargs):
        super().initUI(**kwargs)
        self.layout.addWidget(self.dropDown)
        self.layout.addWidget(self.canvas.native)
        self.image.order = 1
        for c in self.contours.values():
            c.order = 0
        self.dropDown.setStyleSheet(
            """
            QComboBox::item { color: white; background-color : #3E3E3E;}
            QComboBox::item:selected { background-color: #999999;} """
        )

    def update_visible_contours(self, visible_contours):
        for l, c in self.contours.items():
            if l in visible_contours:
                c.parent = self.viewbox.scene
            else:
                c.parent = None

    def update_current_time(self, t):
        self.current_frame_index = min(
            self.timestamps.searchsorted(t), len(self.timestamps) - 1
        )
        if self.is_visible:
            self.update_image()

    def toggle_visiblity(self, *args):
        super().toggle_visiblity(*args)
        if self.is_visible:
            self.update_image()

    def update_image(self):
        name = self.dropDown.currentText()
        if self.current_frame_index is None:
            x = np.zeros(self.dims)
        else:
            x = self.vids[name][self.current_frame_index][:, :, 0] / 255
        image = (np.clip(x, self.vmin, self.vmax) - self.vmin) / (self.vmax - self.vmin)
        self.image.set_data(image.astype(np.float32))
        self.canvas.update()

    def update_colormap_range(self, vmin, vmax):
        self.vmin, self.vmax = vmin, vmax
        self.update_image()

    def show_adjust_colormap_dialog(self):
        self.adjust_colormap_dialog.show()

    def mouse_release(self, event):
        if event.button == 2:
            self.context_menu(event)

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

        # click to show adjust colormap range dialog
        label = add_menu_item("Adjust colormap range", self.show_adjust_colormap_dialog)

        contextMenu.setStyleSheet(
            """
            QMenu::item, QLabel, QCheckBox { background-color : #3E3E3E; padding: 5px 6px 5px 6px;}
            QMenu::item:selected, QLabel:hover, QCheckBox:hover { background-color: #999999;}
            QMenu::separator { background-color: rgb(20,20,20);} """
        )
        action = contextMenu.exec_(event.native.globalPos())

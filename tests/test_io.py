import numpy as np
import snub.io.project
import snub.io.manifold
import os
import shutil
import pytest


@pytest.fixture(scope="session")
def data_directory():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


@pytest.fixture(scope="session")
def project_directory(data_directory):
    """Create a temporary project directory for testing."""

    project_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "tmp_project"
    )
    video_timestamps = np.load(os.path.join(data_directory, "video_timestamps.npy"))
    snub.io.project.create_project(
        project_dir,
        start_time=video_timestamps.min(),
        end_time=video_timestamps.max(),
    )
    yield project_dir
    shutil.rmtree(project_dir)


def test_add_video(project_directory, data_directory):
    """Test snub.io.project.add_video"""

    timestamps_path = os.path.join(data_directory, "video_timestamps.npy")
    video_timestamps = np.load(timestamps_path)

    snub.io.project.add_video(
        project_directory,
        os.path.join(data_directory, "ir_video.mp4"),
        timestamps=video_timestamps,
        name="IR_camera",
    )


def test_add_heatmap(project_directory, data_directory):
    """Test snub.io.project.add_heatmap"""

    annotations_path = os.path.join(data_directory, "behavior_annotations.npy")
    behavior_annotations = np.load(annotations_path)

    labels_path = os.path.join(data_directory, "behavior_labels.txt")
    behavior_labels = open(labels_path, "r").read().split("\n")

    snub.io.project.add_heatmap(
        project_directory,
        "behavior annotations",
        behavior_annotations,
        labels=behavior_labels,
        height_ratio=3,
        start_time=0.1,
        binsize=1 / 30,
    )


def test_add_scatter(project_directory, data_directory):
    """Test snub.io.project.add_scatter and snub.io.manifold.bin_data"""

    coordinates_path = os.path.join(data_directory, "umap_coordinates.npy")
    coordinates = np.load(coordinates_path)

    annotations_path = os.path.join(data_directory, "behavior_annotations.npy")
    behavior_annotations = np.load(annotations_path)
    binned_behavior_annotations = snub.io.manifold.bin_data(behavior_annotations, 6)

    labels_path = os.path.join(data_directory, "behavior_labels.txt")
    behavior_labels = open(labels_path, "r").read().split("\n")

    snub.io.project.add_scatter(
        project_directory,
        "umap embedding",
        coordinates,
        binsize=0.5,
        start_time=6.666,
        pointsize=5,
        variables=binned_behavior_annotations.T,
        variable_labels=behavior_labels,
    )

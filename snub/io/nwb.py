import pynwb
import os
from ndx_pose import PoseEstimation
from ndx_labels import LabelSeries
import numpy as np
import snub.io.project
from vidio import VideoReader


EPS = 1e-6


def create_project_from_nwb(
    project_directory,
    nwb_path,
    branches=["root"],
    use_full_path=True,
    project_options={},
    subplot_options={},
):
    """
    Given an NWB file and a specification of the branches of the file to be visualized,
    this method creates a SNUB project with the file's data.

    Parameters
    ----------
    project_directory : str
        Project path. A directory will be created at this location.

    nwb_path : str
        Path to the NWB file.

    branches : list of str, optional
        A specification of which subtrees of the NWB file (on the basis of their name)
        to include in the SNUB project. If None, all data with a supported type will be
        included.

    use_full_path : bool, optional
        Whether to use the full path in the NWB file when naming the SNUB object
        corresponding to the NWB data. If False, only the name of the leaf node will be
        used. If these names are not unique, an error will be raised.

    project_options, dict
        Additonal key word arguments for snub.io.create_project

    subplot_options, dict
        Additonal key word arguments to be passed to the specific subplot-adding functions
        as a dict mapping dataset names to dicts of options. The names should be full paths
        if use_full_path is True, or just the names of the leaf nodes otherwise.
    """
    nwb_type_mapping = {
        "IntervalSeries": add_interval_series,
        "RoiResponseSeries": add_roi_response_series,
        "TimeSeries": add_generic_timeseries,
        "PoseEstimation": add_pose_estimation,
        "ImageSeries": add_image_series,
        "LabelSeries": add_label_series,
        "TimeIntervals": add_time_intervals,
        "Position": add_position,
        "SpatialSeries": add_spatial_series,
        "Units": add_ephys_units,
        "Events": add_events,
    }

    with pynwb.NWBHDF5IO(nwb_path, mode="r", load_namespaces=True) as io:
        nwbfile = io.read()

        # Get all datasets to be included
        children = list_included_datasets(nwbfile, branches, nwb_type_mapping)
        print("The following datasets will be included in the SNUB plot:")
        for child in children:
            print(f"  {_generate_name(child, use_full_path)} ({child.neurodata_type})")
        print("")

        # Check that there is at least one dataset to be included
        assert len(children) > 0, (
            "No datasets found in NWB file that match the specified branch names and have"
            " one of the following supported types: " + str(nwb_type_mapping.keys())
        )

        # Check that all datasets to be included have unique names
        if not use_full_path:
            names = [c.name for c in children]
            assert len(names) == len(set(names)), (
                "Not all datasets to be included have unique names. You must set "
                "use_full_path=True to resolve this."
            )

        # Create project
        start_time, end_time = _get_start_end_times(children)
        snub.io.project.create_project(
            project_directory,
            start_time=start_time,
            end_time=end_time,
            **project_options,
        )

        # Add data
        for child in children:
            name = _generate_name(child, use_full_path)

            if name in subplot_options:
                opts = subplot_options[name]
            else:
                opts = {}

            try:  # try/except catches malformed data
                nwb_type_mapping[child.neurodata_type](
                    project_directory, child, name, start_time, end_time, opts
                )
            except Exception as e:
                print(f"Skipping data {name} because of error: {e}")


def _get_start_end_times(objects):
    """
    Given a list of objects from an NWB file, returns the earliest and latest timestamps
    from the object or its children.
    """
    starts, ends = [], []
    for obj in objects:
        if obj.neurodata_type == "PoseEstimation":
            s, e = _get_start_end_times(obj.pose_estimation_series.values())
        elif obj.neurodata_type == "Position":
            s, e = _get_start_end_times(obj.spatial_series.values())
        elif obj.neurodata_type == "Units":
            s = obj.spike_times[()].min()
            e = obj.spike_times[()].max()
        elif obj.neurodata_type == "TimeIntervals":
            s = obj.start_time[()].min()
            e = obj.stop_time[()].max()
        else:
            print(obj.neurodata_type, obj.name)
            timestamps = get_timestamps(obj)
            s = timestamps.min()
            e = timestamps.max()
        starts.append(s)
        ends.append(e)
    return min(starts), max(ends)


def list_included_datasets(nwbfile, branches, nwb_type_mapping):
    """
    Enumerates all datasets in an NWB file that should be included in the SNUB project.

    Datasets are included if (a) their type is supported and (b) they belong to one of
    the branches specified by the user. If an included dataset is the child of another
    dataset, only the parent will be included (e.g. when a Position dataset is included,
    its child SpatialSeries datasets will not be included). Datasets are also excluded
    if they have a "rate" parameter that is set to 0.
    """
    included_datasets = []
    for child in nwbfile.all_children():
        ancestors = child.get_ancestors()
        ancestor_names = [a.name for a in ancestors] + [child.name]

        has_supported_type = child.neurodata_type in nwb_type_mapping
        from_included_branch = len(set(branches).intersection(ancestor_names)) > 0
        has_no_included_parents = (
            len([c for c in included_datasets if c in ancestors]) == 0
        )
        has_valid_rate = (not "rate" in child.fields) or (child.rate > 0)

        if np.all(
            [
                has_supported_type,
                from_included_branch,
                has_no_included_parents,
                has_valid_rate,
            ]
        ):
            included_datasets.append(child)

    return included_datasets


def get_timestamps(obj):
    """
    Get timestamps for a TimeSeries object or ImageSeries object.

    Parameters
    ----------
    obj: pynwb.TimeSeries or pywnb.ImageSeries
        NWB TimeSeries or ImageSeries object.
    """
    if obj.timestamps is None:
        # Get start time
        if "start" in obj.fields:
            start = obj.start
        elif "starting_time" in obj.fields:
            start = obj.starting_time
        else:
            raise AssertionError(
                f"TimeSeries {obj.name} has no start time. Cannot determine timestamps."
            )

        # Get rate
        if "rate" not in obj.fields:
            raise AssertionError(
                f"TimeSeries {obj.name} has no rate. Cannot determine timestamps."
            )
        rate = obj.rate

        # Get duration
        if obj.neurodata_type == "ImageSeries":
            T = len(VideoReader(obj.external_file[0]))
        else:
            T = len(obj.data)

        # Compute timestamps
        stamps = start + np.arange(T) / rate
    else:
        stamps = obj.timestamps[:]
    stamps = stamps.astype(float)
    return stamps


def _timestamps_to_intervals(timestamps):
    """
    Given an array of timestamps, returns an array of intervals that are centered on the
    timestamps and have width determined by the inter-timestamp intervals.
    """
    starts = np.hstack(
        [
            [timestamps[0] - (timestamps[1] - timestamps[0]) / 2],
            (timestamps[1:] + timestamps[:-1]) / 2,
        ]
    )
    ends = np.hstack(
        [
            (timestamps[1:] + timestamps[:-1]) / 2,
            [timestamps[-1] + (timestamps[-1] - timestamps[-2]) / 2],
        ]
    )
    return np.vstack([starts, ends]).T


def _generate_name(child, use_full_path):
    if use_full_path:
        return ".".join(
            [a.name for a in list(child.get_ancestors())[:-1][::-1] + [child]]
        )
    else:
        return child.name


def add_interval_series(project_directory, obj, name, start_time, end_time, options):
    """
    Adds an interval series to a SNUB project in the form of a traceplot.
    """
    print(f'Adding interval series "{name}" as a traceplot.')
    timestamps = obj.timestamps[()]  # contains start and end times
    data = obj.data[()]  # contains interval types numbers: + for start, - for end

    traces = {}
    interval_types = set(data[data > 0])
    for i in interval_types:
        trace = [[start_time, 0]]
        starts = timestamps[data == i]
        ends = timestamps[data == -i]
        for start, end in zip(starts, ends):
            trace.append([start - EPS, 0])
            trace.append([start, 1])
            trace.append([end - EPS, 1])
            trace.append([end, 0])
        trace.append([end_time, 0])
        traces[str(i)] = np.array(trace)

    snub.io.project.add_traceplot(project_directory, name, traces, **options)


def add_roi_response_series(
    project_directory, obj, name, start_time, end_time, options
):
    """
    Adds an ROI response series to a SNUB project in the form of a heatmap.
    """
    print(f'Adding ROI response series "{name}" as a heatmap.')
    data = obj.data[()].T
    start_time = obj.starting_time
    binsize = 1 / obj.rate

    snub.io.project.add_heatmap(
        project_directory,
        name,
        data,
        start_time=start_time,
        binsize=binsize,
        **options,
    )


def add_spatial_series(project_directory, obj, name, start_time, end_time, options):
    """
    Adds a spatial series to a SNUB project in the form of a traceplot.
    """
    print(f"Adding spatial series {name} as a traceplot.")
    data = obj.data[()]
    timestamps = get_timestamps(obj)

    if len(data.shape) == 1:
        data = data[:, None]

    traces = {}
    for i in range(data.shape[1]):
        trace = np.vstack([timestamps, data[:, i]]).T
        traces[f"dim {i}"] = trace

    snub.io.project.add_traceplot(project_directory, name, traces, **options)


def add_position(project_directory, obj, name, start_time, end_time, options):
    """
    Adds position data to a SNUB project in the form of a traceplot.
    """
    print(f'Adding positions "{name}" as a traceplot.')

    traces = {}
    for key, child in obj.spatial_series.items():
        timestamps = get_timestamps(child)
        positions = child.data[()]
        if len(positions.shape) == 1:
            trace = np.vstack([timestamps, positions]).T
            traces[key] = trace
        else:
            for i in range(positions.shape[1]):
                trace = np.vstack([timestamps, positions[:, i]]).T
                traces[f"{key} (dim {i})"] = trace

    snub.io.project.add_traceplot(project_directory, name, traces, **options)


def add_generic_timeseries(
    project_directory, obj, name, start_time, end_time, options, heatmap_threshold=10
):
    """
    Adds a generic timeseries to a SNUB project in the form of a traceplot or heatmap,
    depending on the number of dimensions.
    """
    data = obj.data[()]
    timestamps = get_timestamps(obj)

    if len(data.shape) == 1:
        data = data[:, None]

    if data.shape[1] > heatmap_threshold:
        print(f'Adding generic timeseries "{name}" as a heatmap.')
        snub.io.project.add_heatmap(
            project_directory,
            name,
            data.T,
            time_intervals=_timestamps_to_intervals(timestamps),
            **options,
        )
    else:
        print(f'Adding generic timeseries "{name}" as a traceplot.')
        traces = {}
        for i in range(data.shape[1]):
            trace = np.vstack([timestamps, data[:, i]]).T
            traces[f"dim-{i}"] = trace

        snub.io.project.add_traceplot(project_directory, name, traces, **options)


def add_pose_estimation(project_directory, obj, name, start_time, end_time, options):
    """
    Adds pose estimation to a SNUB project in the form of a traceplot (and a 3D pose plot
    if the pose estimation is 3D).
    """
    print(f'Adding pose estimation "{name}" as a traceplot.')

    joint_labels = obj.nodes[:]
    keypoints, traces = [], {}
    for joint in joint_labels:
        child = obj.pose_estimation_series[joint]
        timestamps = get_timestamps(child)
        keypoints.append(child.data[()])
        for i in range(child.data.shape[1]):
            label = f"{joint}-{['x','y','z'][i]}"
            trace = np.vstack([timestamps, child.data[:, i]]).T
            traces[label] = trace

    snub.io.project.add_traceplot(project_directory, name, traces, **options)

    if keypoints[-1].shape[1] == 3:
        print(f'Adding pose estimation "{name}" as a 3D pose plot.')
        snub.io.project.add_pose3D(
            project_directory,
            name,
            np.stack(keypoints, axis=1),
            links=obj.edges[:],
            time_intervals=_timestamps_to_intervals(timestamps),
        )


def add_image_series(project_directory, obj, name, start_time, end_time, options):
    """
    Adds an image series to a SNUB project in the form of a video.
    """
    print(f'Adding image series "{name}" as a video.')
    timestamps = get_timestamps(obj)
    for path in obj.external_file:
        if not os.path.exists(path):
            print(f"Warning: external file {path} does not exist. Skipping.")
        else:
            snub.io.project.add_video(
                project_directory, path, name, timestamps=timestamps, **options
            )


def add_label_series(project_directory, obj, name, start_time, end_time, options):
    """
    Adds a label series to a SNUB project in the form of a heatmap.
    """
    print(f'Adding label series "{name}" as a heatmap.')
    data = obj.data[()].T
    timestamps = get_timestamps(obj)
    labels = obj.vocabulary[:]

    snub.io.project.add_heatmap(
        project_directory,
        name,
        data,
        time_intervals=_timestamps_to_intervals(timestamps),
        labels=labels,
        **options,
    )


def add_time_intervals(project_directory, obj, name, start_time, end_time, options):
    """
    Adds a time intervals to a SNUB project in the form of a traceplot.
    """
    print(f'Adding time intervals "{name}" as a traceplot.')

    ignored_fields = [
        n for n in obj.colnames if n not in ["start_time", "stop_time", "timeseries"]
    ]
    if ignored_fields:
        print(f'Warning: ignoring fields {ignored_fields} in time intervals "{name}"')

    starts = obj.start_time[()]
    ends = obj.stop_time[()]
    trace = [[start_time, 0]]
    for start, end in zip(starts, ends):
        trace.append([start - EPS, 0])
        trace.append([start, 1])
        trace.append([end - EPS, 1])
        trace.append([end, 0])
    trace.append([end_time, 0])
    traces = {"intervals": np.array(trace)}
    snub.io.project.add_traceplot(project_directory, name, traces, **options)


def add_ephys_units(project_directory, obj, name, start_time, end_time, options):
    """
    Adds ephys units to a SNUB project in the form of a spikeplot.
    """
    print(f'Adding ephys units "{name}" as a spikeplot.')

    spike_times_per_unit = obj.to_dataframe()["spike_times"]
    spike_times = np.hstack(spike_times_per_unit)
    spike_labels = np.hstack(
        [np.ones(len(spikes)) * i for i, spikes in enumerate(spike_times_per_unit)]
    )
    snub.io.project.add_spikeplot(
        project_directory,
        name,
        spike_times,
        spike_labels,
        **options,
    )


def add_events(project_directory, obj, name, start_time, end_time, options):
    """
    Adds events to a SNUB project in the form of a traceplot.
    """
    print(f'Adding events "{name}" as a traceplot.')

    trace = [(start_time, 0)]
    for t in obj.timestamps[()]:
        trace.append((t - EPS, 0))
        trace.append((t, 1))
        trace.append((t + EPS, 0))
    trace.append((end_time, 0))
    traces = {"events": np.array(trace)}
    snub.io.project.add_traceplot(project_directory, name, traces, **options)

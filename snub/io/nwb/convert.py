"""
Methods for converting NWB files into SNUB projects.
"""

from os.path import basename

import numpy as np

from pynwb import NWBHDF5IO
from .nwb_tree import NWBTree

import snub.io.project

def create_project_from_nwb(
    project_directory,
    nwb_path,
    branches=None,
    use_branch_name=True,
    **kwargs
):
    """
    Given an NWB file and a specification of the branches
    of the file to be visualized, this method creates a
    SNUB project with the file's data.

    Parameters
    ----------
    project_directory : str
        Project path. A directory will be created at this location.
    
    nwb_path : str
        File path to the NWB file. 
    
    branches : None or str or Tuple[str] or Tuple[Tuple[str]], optional
        A specification of which subtrees of the NWB file (on
        the basis of their path from the file root) to populate the
        SNUB directory with. If None, the whole file will be crawled.
        To get a sense for the expected format, see _format_branches.
    
    use_branch_name : bool, optional
        Whether to use the full path in the NWB file when naming the
        SNUB object corresponding to the NWB data. If False, only the
        name of the leaf node will be used, in which case the client
        is responsible for ensuring that each leaf node has a unique name.

    **kwargs
        key word arguments for snub.io.create_project
    """
    with NWBHDF5IO(nwb_path, mode='r') as io:
        nwbfile = io.read()
        tree = NWBTree(nwbfile)
        start_time, end_time = _get_duration(tree)
        snub.io.project.create_project(project_directory,
                                       start_time=start_time,
                                       end_time=end_time,
                                       **kwargs)
    add_nwb(project_directory, nwb_path,
            branches, use_branch_name)

def add_nwb(
    project_directory,
    nwb_path,
    branches=None,
    use_branch_name=True
):
    """
    Given an NWB file and a specification of the branches
    of the file to be visualized, this method adds the queried
    data to an existing SNUB project directory.

    Parameters
    ----------
    project_directory : str
        Project path containing SNUB config file.
    
    nwb_path : str
        File path to the NWB file. 
    
    branches : None or str or Tuple[str] or Tuple[Tuple[str]], optional
        A specification of which subtrees of the NWB file (on
        the basis of their path from the file root) to populate the
        SNUB directory with. If None, the whole file will be crawled.
        To get a sense for the expected format, see _format_branches.
    
    use_branch_name : bool, optional
        Whether to use the full path in the NWB file when naming the
        SNUB object corresponding to the NWB data. If False, only the
        name of the leaf node will be used, in which case the client
        is responsible for ensuring that each leaf node has a unique name.
    """
    branches = _format_branches(branches)
    with NWBHDF5IO(nwb_path, mode='r') as io:
        nwbfile = io.read()
        tree = NWBTree(nwbfile)
        for branch in branches:
            subtree = _get_branch(tree, branch)
            _add_recursive(project_directory, subtree, branch, use_branch_name)

def _get_duration(tree, round_seconds=True):
    """
    Given an NWBTree, this method determines the temporal
    interval spanned by the data it contains.

    Parameters
    ----------
    tree : NWBTree
        NWBTree object wrapping the file structure.
    
    round_seconds : bool, optional
        Whether to round the interval to the nearest second.

    Returns
    -------
    start : float
        Starting time, in seconds.
    
    end : float
        Ending time, in seconds.
    """
    if tree.is_leaf():
        stamps = tree.get_timestamps()
        start = stamps[0]
        end = stamps[-1]
        if round_seconds:
            start = np.floor(start)
            end = np.ceil(end)
    else:
        start = np.inf
        end = -np.inf
        for child in tree.values():
            start_child, end_child = _get_duration(child, round_seconds)
            start = min(start, start_child)
            end = max(end, end_child)
    return start, end

def _format_branches(branches):
    """
    Given the branches to crawl, as provided by the client,
    this function reformats them as a list of tuples of strings,
    where each tuple specifies the sequence of keys to index.

    Parameters
    ----------
    branches : None or str or Tuple[str] or Tuple[Tuple[str]]
        Branches as specified by the client.

    Returns
    -------
    reformatted : List[Tuple[str]]
        Branches in the correct format.
    """
    # None, empty string -> root node
    if not branches:
        return [tuple()]
    
    # string or container of strings
    if isinstance(branches[0], str):
        branches = [branches]
    
    reformatted = []
    for branch in branches:
        if isinstance(branch, str):
            reformatted.append((branch,))
        else:
            reformatted.append(tuple(branch))
    return reformatted

def _get_branch(tree, branch):
    """
    Given a branch (i.e. a list of keys specifying the
    sequence of hops from the root to some subtree), this
    method returns the specified subtree.

    Parameters
    ----------
    tree : NWBTree
        Tree to traverse.
    
    branch : tuple
        Tuple specifying path from root of tree to desired subtree.

    Returns
    -------
    subtree : NWBTree
        Subtree specified by branch.
    """
    subtree = tree
    for key in branch:
        subtree = subtree[key]
    return subtree

def _add_recursive(project_directory, tree, branch, use_branch_name=True):
    """
    Recursively traverses the file tree, adding the data for
    each leaf node to the snub project dir.

    Parameters
    ----------
    project_directory : str
        SNUB directory to add the data to.

    tree : NWBTree
        Tree object with root at position specified by branch.
    
    branch : tuple
        Tuple of keys specifying path from root to tree.
    
    use_branch_name : bool, optional
        Whether to name the data by the full branch or the leaf.
    """
    if _is_recursive_case(tree):
        for key, subtree in tree.items():
            _add_recursive(project_directory, subtree,
                           branch + (key,), use_branch_name)
        return

    if use_branch_name:
        name = '.'.join(branch)
    else:
        name = branch[-1]

    if tree.is_video():
        _add_video(project_directory, tree, name)
    elif tree.is_keypoints():    # base cases
        _add_keypoints(project_directory, tree, name)
    elif tree.is_labels():
        _add_labels(project_directory, tree, name)
    else:
        _add_timeseries(project_directory, tree, name)

def _is_recursive_case(tree):
    """
    Helper method for _add_recursive that determines
    whether the current tree is a recursive or base case.

    Parameters
    ----------
    tree : NWBTree
        File tree object.

    Returns
    -------
    is_recursive_case : bool
        Self-explanatory.
    """
    return not (tree.is_leaf() or tree.is_keypoints())

def _add_video(project_directory, tree, name):
    """
    Given a leaf node that stores an NWB ImageSeries, adds
    the corresponding video to the SNUB directory.

    Parameters
    ----------
    project_directory : str
        SNUB directory to add the data to.

    tree : NWBTree
        File tree object.
    
    name : str
        Name to add to the SNUB project directory.
    """
    timestamps = tree.get_timestamps()
    for path in tree.obj.external_file:
        video_name, _ = basename(path).rsplit('.', 1)
        video_name = f'{name}.{video_name}'
        snub.io.project.add_video(project_directory,
                                  path, name=video_name,
                                  timestamps=timestamps)

def _add_keypoints(project_directory, tree, name):
    """
    Given a leaf node that stores an NWB PoseEstimation,
    adds the corresponding 3D keypoints to the SNUB directory.

    Parameters
    ----------
    project_directory : str
        SNUB directory to add the data to.

    tree : NWBTree
        File tree object.
    
    name : str
        Name to add to the SNUB project directory.
    """
    joint_labels = tree.obj.nodes[:]
    links = tree.obj.edges[:]
    
    keypoints = []
    for joint in joint_labels:
        data, timestamps = tree[joint].get_both()
        keypoints.append(data)
    keypoints = np.stack(keypoints, 1)

    _add_generic(project_directory, keypoints, timestamps, name,
                 links=links, joint_labels=joint_labels)

def _add_labels(project_directory, tree, name, colormap='gray'):
    """
    Given a leaf node that stores an NWB LabelSeries, adds
    the corresponding labels to the SNUB directory.

    Parameters
    ----------
    project_directory : str
        SNUB directory to add the data to.
        
    tree : NWBTree
        File tree object.
    
    name : str
        Name to add to the SNUB project directory.
    
    colormap : str, optional
        Name of matplotlib colormap to use. 
    """
    data, timestamps = tree.get_both()
    labels = tree.obj.vocabulary[:]
    _add_generic(project_directory, data, timestamps, name,
                 labels=labels, colormap=colormap)

def _add_timeseries(project_directory, tree, name, colormap='plasma'):
    """
    Given a leaf node that stores an NWB TimeSeries, adds
    the corresponding data to the SNUB directory.

    Parameters
    ----------
    project_directory : str
        SNUB directory to add the data to.

    tree : NWBTree
        File tree object.
    
    name : str
        Name to add to the SNUB project directory.
    
    colormap : str, optional
        Name of matplotlib colormap to use. 
    """
    data, timestamps = tree.get_both()
    _add_generic(project_directory, data, timestamps, name, colormap=colormap)
    
def _add_generic(project_directory, data, timestamps, name, **kwargs):
    """
    Adds the data to SNUB project. Infers the data type based on
    the number of dimensions in the input array. If the array is
    one-dimensional, it is added as trace; if it's two dimensional,
    it's added as a heatmap; and if it's a three dimensional, it's
    added as a 3D pose.

    Parameters
    ----------
    project_directory : str
         SNUB directory to add the data to.

    data : np.array
        One-dimensional data signal.
    
    timestamps : np.array
        Time stamps corresponding to datapoints.
    
    name : str
        Name to add to the SNUB project directory.
    """
    if data.ndim == 1:
        return _add_trace(project_directory, data, timestamps, name)
    
    time_intervals = _stamps_to_intervals(timestamps)
    if data.ndim == 2:
        data = data.T # (time, vars) - > (vars, time)
        io_function = snub.io.project.add_heatmap
    elif data.ndim == 3:
        io_function = snub.io.project.add_pose3D
    else:
        raise ValueError('Data must be 1, 2, or 3 dimensional.')
    
    io_function(project_directory, name, data,
                time_intervals=time_intervals, **kwargs)
    
def _add_trace(project_directory, data, timestamps, name):
    """
    Adds the data to SNUB project as a trace plot.

    Parameters
    ----------
    project_directory : str
         SNUB directory to add the data to.

    data : np.array
        One-dimensional data signal.
    
    timestamps : np.array
        Time stamps corresponding to datapoints.
    
    name : str
        Name to add to the SNUB project directory.
    """
    trace_name = name.rsplit('.', 1)[-1]
    traces = {trace_name: np.stack((timestamps, data), -1)}
    snub.io.project.add_traceplot(project_directory, name, traces)

def _stamps_to_intervals(timestamps):
    """
    Converts an array of timestamps to an array of intervals
    for each data point.

    Parameters
    ----------
    timestamps : np.array
        Times corresponding to each data point.

    Returns
    -------
    intervals : np.array
        Array of shape (T, 2) specifying the time interval for each point
    """
    min_step = np.min(timestamps[1:] - timestamps[:-1])
    end = timestamps[-1] + min_step

    starts = timestamps
    ends = np.r_[timestamps[1:], end]
    intervals = np.stack((starts, ends), -1)
    return intervals

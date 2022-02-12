import numpy as np
import json
import os
import shutil
import pprint
import warnings
import pickle
import colorsys
from vidio import VideoReader

def generate_intervals(start_time, binsize, num_intervals):
    """Generate an array of start/end times for non-overlapping
    time intervals.

    Parameters
    ----------
    start_time: float
        Left bound of the first time interval

    binsize: float
        Width of each interval

    num_intervals: int

    Returns
    -------
        time_intervals: ndarray
            Array of shape (num_intervals,2) containing the start 
            and end times for each interval.
    """
    starts = np.arange(num_intervals)*binsize+start_time
    ends = np.arange(1,num_intervals+1)*binsize+start_time
    time_intervals = np.vstack((starts,ends)).T
    return time_intervals


def create_project(
    project_directory, 
    overwrite=False,
    start_time=0,
    duration=None, 
    end_time=None,
    layout_mode='columns',
    tracks_size_ratio=2,
    panels_size_ratio=1,
    min_step=1/30,
    animation_fps=30,
    zoom_gain=0.001,
    min_range=.25,
    init_current_time=None,
    initial_playspeed=1,
    center_playhead=False,
):
    """Set up a new SNUB project by creating a directory and config.json file. 

    Parameters
    ----------
    project_directory : str 
        Project path. A directory will be created at this location.

    overwrite : bool, default=False
        If a config.json file already exists in the project directory,
        overwrite=True will cause the file to be overwritten. To edit
        but not overwrite an existing config file, use :py:func:`snub.io.project.edit_config`.
        
    start_time : float, default=0
        Lower bound (in seconds) of the timeline in the SNUB browser.
        
    duration : float, default=None
        Sets the upper bound of the timeline in the SNUB browser. 
        If ``duration`` is not None, the timeline will bounds will be 
        [start_time,start_time+duration] in seconds. Alternatively, 
        the upper bound can be set using the ``end_time`` argument.

    end_time : float, default=None
        Sets the upper bound of the timeline in the SNUB browser. 
        If ``end_time`` is not None, the timeline will bounds will be 
        [start_time,end_time] in seconds. The upper bound can also
        be set using the ``duration`` argument.
        
    layout_mode : {'columns', 'rows'}, default='columns'
        Sets the layout mode when the project is first opened.
        
    tracks_size_ratio: int, default=2
        Relative space initially allocated to the track stack, as opposed to the 
        panel stack. The spacing can also be adjusted within the browser. 
    
    panels_size_ratio: int, default=1
        Relative space initially allocated to the panel stack, as opposed to the 
        panel stack. The spacing can also be adjusted within the browser. 
        
    min_step: float, default=0.033
        Though time is represented continuously in SNUB. Some analyses
        and GUI elements require time to be discretized. In such cases
        ``min_step`` determines the size of each discrete time unit.
        
    animation_fps: float, default=30
        Sets the update rate during playback. If you have
        video data, it is recommended that ``animation_fps`` be
        set to the video framerate, though this is not required
        for realtime playback.
        
    zoom_gain: float, default=0.003
        How fast the timeline zooms in response to scrolling.
        
    min_range: float, default=0.01
        Smallest allowable range in seconds that can be displayed on 
        the timeline. Lower values allow the timeline to be dilated more. 
        
    init_current_time: float, default=None
        SNUB contains a global ``current_time`` variable that sets 
        the location of the playhead, the currently displayed video
        frame, etc. ``init_current_time`` sets the ``current_time`` when
        SNUB is first opened. If ``init_current_time=None``, the current
        time is set the lower bound of the timeline. 
        
    initial_playspeed: float, default=1
        Initial setting for playback speed. The playback speed can 
        be changed at any time within the browser using a slider.
        
    center_playhead: bool, default=False
        Toggles the center-playhead setting. When this setting is 
        True, the playhead stays fixed and the data scrolls by. 
        Otherwise currently visible range rests while the playhead
        moves across the screen.
    
    Returns
    -------
    config: dict
        Config file for the newly created project
    """
    # check for problems with the input
    if os.path.exists(os.path.join(project_directory,'config.json')):
        if overwrite:
            warnings.warn('The directory {} already exists. The config file will be overwritten, but existing data files will be left in place.'.format(project_directory))
        else:
            raise AssertionError(
                'This project already exists. Set `overwrite=True` or use `snub.io.project.edit_config`'
            )
    if duration is None and end_time is None:
        raise AssertionError(
            'Either `duration` or `end_time` must be specified'
        )
    elif duration is not None and end_time is not None and duration != (end_time-start_time):
        raise AssertionError(
            '`duration={}` is inconsistent with `start_time-end_time={}`'.format(duration, end_time-start_time)
        )
        
    # create the config file
    if end_time is None: end_time = start_time + duration
    if init_current_time is None: init_current_time = start_time
    if (end_time-start_time)/min_step > 200000: 
        raise AssertionError('min_step={} is too small for the total duration {}. The maximum allowed ratio of `duration/min_step` is 200,000'.format(min_step, start_time-end_time))

    config = {
        'bounds': [start_time,end_time],
        'layout_mode': layout_mode,
        'panels_size_ratio':panels_size_ratio,
        'tracks_size_ratio':tracks_size_ratio,
        'min_step': min_step,
        'animation_fps':animation_fps,
        'zoom_gain': zoom_gain,
        'min_range': min_range,
        'init_current_time':init_current_time,
        'initial_playspeed': initial_playspeed,
        'center_playhead': center_playhead, 
        'video':[],
        'scatter':[],
        'mesh':[],
        'heatmap':[],
        'spikeplot':[],
        'traceplot':[],
    }
        
    # create the project directory and config file
    if not os.path.exists(project_directory): 
        os.makedirs(project_directory)
    print('Created project "{}"\n'.format(project_directory))
    save_config(project_directory, config)
    return config
    

def load_config(project_directory):
    """Load the config file in a given project directory
    """
    config_path = os.path.join(project_directory, 'config.json')
    if not os.path.exists(config_path):
        raise AssertionError(
            'There is no config file in the project directory. Use `snub.io.project.create_project` to create a new config file')
        
    config = json.load(open(config_path,'r'))
    return config

def save_config(project_directory, config):
    """Save the config dict to the given project directory
    """
    config_path = os.path.join(project_directory,'config.json')
    json.dump(config, open(config_path,'w'), indent=4)
    print('Saved config file '+config_path)
    return config   

def list_dataviews(project_directory):
    """List of the names of each type of dataview
    """
    config = load_config(project_directory)
    for dataview_type in ['video','scatter','mesh','heatmap','spikeplot','traceplot']:
        if dataview_type in config and len(config[dataview_type])>0:
            print(dataview_type+':')
            for props in config[dataview_type]:
                if not 'name' in props: name = '(not named)'
                else: name = props['name']
                print('\t'+name)

def _get_named_dataview_index(config, dataview_type, name):
    """Check if the list of data-views contains a data-view with the
    given name. If so, return its index in the list. If not, return None.
    """
    dataview_list = config[dataview_type]
    indexes = [i for i,d in enumerate(dataview_list) if d['name']==name]
    return None if len(indexes)==0 else indexes[0]
   
def _confirm_no_existing_dataview(config, dataview_type, name):
    index = _get_named_dataview_index(config, dataview_type, name)
    if index is not None:
        raise AssertionError(
            'There is already a {} with the name "{}". Use `snub.io.project.edit_dataview_properties to change its properties, or remove using `snub.io.project.remove_dataview`'.format(dataview_type, name))
    
    
def _random_color():
    hue = np.random.uniform(0,1)
    saturation,value = 1,1
    return [int(255*x) for x in colorsys.hsv_to_rgb(hue,1, 1)]

def edit_global_config(project_directory, **kwargs):
    """Edit the properties in an existing config file by
    inputting the desired key-value pairs as keyword arguments 
    to this function. This function is for editing global properties. 
    To change the properties of a specific data-view, use 
    :py:func:`edit_dataview_properties`. 
    
    Parameters
    ----------
    project_directory : str 
        Project path containing the config.json file.
    """
    config = load_config(project_directory)
    for key,value in kwargs.items():
        config[key] = value
    save_config(project_directory, config)
    
    
def set_markers(project_directory, markers):
    """Set the time markers for a project. Any existing
    time markers are overwritten and replaced by the contents of the 
    ``markers`` argument. 
    
    Time markers are vertical lines over the SNUB timeline
    that can be used to marker key events such as trials.
    
    Parameters
    ----------
    project_directory : str 
        Project path containing the config.json file.

    markers : dict
        Dictionary containing the desired time markers. Entries should consist of 
        key-value pairs where the key is the name of the marker and the value
        is a dict of the form ``{'time': float, 'color': (int,int,int)}``. For example
        to mark a pair of trials at 10sec and 20sec with white lines, set
        
        .. code-block:: python
        
            markers = {
                'trial 1': {'time': 10, 'color': (255,255,255)},
                'trial 2': {'time': 20, 'color': (255,255,255)}
            }
    """
    config = load_config(project_directory)
    config['markers'] = props
    save_config(project_directory, config)


def edit_dataview_properties(project_directory, dataview_type, name, **kwargs):
    """Edit the properties of a data-view by inputting the desired 
    key-value pairs as keyword arguments to this function. 
    
    Parameters
    ----------
    project_directory : str 
        Project path containing the config.json file.

    dataview_type : {'video', 'scatter', 'mesh', 'heatmap', 'spikeplot', 'traceplot'}
        The type of data-view to be edited.

    name: str
        Name of the data-view to be edited. 
    """
    config = load_config(project_directory)
    index = _get_named_dataview_index(config, dataview_type, name)
    if index is None:
        raise AssertionError(
            'The project does not contain a {} with the name "{}"'.format(dataview_type, name)
        )
    props = config[dataview_type][index]
    for key,value in kwargs.items():
        props[key] = value 
    config[dataview_type][index] = props
    save_config(project_directory, config)
    

def remove_dataview(project_directory, dataview_type, name, delete_data=False):
    """Remove a data-view from the specified project and (optionally)
    delete its data.
    
    Parameters
    ----------
    project_directory : str 
        Path of the project to be edited.

    dataview_type : {'video', 'scatter', 'mesh', 'heatmap', 'spikeplot', 'traceplot'}
        The type of data-view to be removed.

    name: str
        Name of the data-view to be remove.
        
    delete_data: bool, default=False
        Delete the data associated with the given data-view, which may
        be .avi, .npy or .hdf5 files depending on the type of data-view.
    """
    
    config = load_config(project_directory)
    index = _get_named_dataview_index(config, dataview_type, name)
    if index is None:
        raise AssertionError(
            'The project does not contain a {} with the name "{}"'.format(dataview_type, name)
        )
    if delete_data:
        for key,value in config[dataview_type][index].items():
            if 'path' in key:
                data_path = os.path.join(project_directory,value)
                if os.path.exists(data_path):
                    print('Deleting',data_path)
                    os.remove(data_path)
    del config[dataview_type][index]
    print('Removed {} with the name "{}"'.format(dataview_type, name))
    save_config(project_directory, config) 
    


def add_video(
    project_directory,
    videopath,
    copy=True,
    name=None, 
    fps=30,
    start_time=0,
    timestamps=None, 
    size_ratio=1,
    order=0,
):
    """Add a video to your SNUB project. 
    
    Parameters
    ----------
    project_directory : str 
        Project that the video should be added to.
        
    videopath : str
        Path to an existing video. The video will be read as 8bit RGB.
        Other video formats, such as 16bit depth or 16bit monochrome,
        will have to be converted to 8bit RGB before they can be added.
        Functions for doing so are provided in :py:mod:`snub.io.video_conversion`.
        
    copy: bool, default=True
        It is recommended that all data for a given project is contained
        within the project directory. Leave ``copy=True`` if the video file 
        is currently outside the project directory and you wish to copy it.
        Otherwise if ``copy=False``, the config will store the relative path
        from the project directory to the video file. 
        
    name: str, default=None
        The name of the video, which is displayed in SNUB and can be used
        to edit the config file. If no name is given, the video's filename
        will be used. 
        
    fps: float, default=30
        The video framerate. This parameter is used in conjunction with
        ``start_time`` to generate a timestamps file, unless an array of 
        timestamps is directly provided. 
        
    start_time: float, default=0
        The start time of the video (in seconds). This parameter is used 
        in conjunction with ``fps`` to generate a timestamps file, unless an 
        array of timestamps is directly provided. 
        
    timestamps: str/array-like, default=None
        Array of timestamps in units of seconds.
        ``timestamps`` can either be an array, or the path to .npy file, 
        or the path to a text file with a timestamp on each line. If 
        ``timestamps=None``, the timestamps will be created from
        ``fps`` and ``start_time``.

    size_ratio: int, default=1
        The relative space initially allocated to this data-view in the panel-stack. 
        Spacing can also be adjusted within the browser. 
        
    order: float, default=0
        Determines the order of placement within the panel-stack.
        Panels are arranged top-to-bottom (in column mode) or 
        left-to-right (row mode) by ascending rank of the ``order`` property.
        
    Returns
    -------
    props: dict
        video properties
    """    
    # check that project exists and video with given name does not exist
    if not os.path.exists(videopath):
        raise AssertionError('The file "{}" does not exist'.format(videopath))
    
    if name is None: 
        name = os.path.splitext(os.path.basename(videopath))[0]
        
    config = load_config(project_directory)
    _confirm_no_existing_dataview(config, 'video', name)
    
    # load/create timestamps and save as .npy
    if timestamps is None:
        video_length = len(VideoReader(videopath))
        timestamps = np.arange(video_length)/fps + start_time
        print('Creating timestamps array with start_time={}, fps={}, and n_frames={}'.format(start_time, fps, video_length))
        
    elif isinstance(timestamps,str):
        if timestamps.endswith('.npy'):
            timestamps = np.load(timestamps)
        elif timestamps.endswith('.txt'):
            timestamps = np.loadtxt(timestamps)
        else:
            raise AssertionError('If given as a path, `timestamps` must have extension .npy or .txt')
    
    timestamps_path_rel = name+'.timestamps.npy'
    timestamps_path_abs = os.path.join(project_directory, timestamps_path_rel)
    np.save(timestamps_path_abs, timestamps)
    print('Saved timestamps to '+timestamps_path_abs)

    # optionally copy video
    if copy:
        videopath_rel = name+os.path.splitext(videopath)[1]
        videopath_abs = os.path.join(project_directory, videopath_rel)
        if not os.path.exists(videopath_abs):
            shutil.copy(videopath, videopath_abs)
            print('Copying video to '+videopath_abs)
    else:
        videopath_rel = os.path.relpath(videopath, start=project_directory)
        
    # add props to config
    props = {
        'name': name,
        'video_path': videopath_rel,
        'timestamps_path': timestamps_path_rel,
        'size_ratio': size_ratio,
        'order': order,
    }
    config['video'].append(props)
    print('Added video plot "{}"\n'.format(name))
    save_config(project_directory, config)
    return props
   
    
    
def add_traceplot(
    project_directory,
    name,
    traces,
    linewidth=1, 
    trace_colors={},
    bgcolor=(0,0,0),
    height_ratio=1,
    order=0,
):
    """Add a traceplot to your SNUB project.
    
    Parameters
    ----------
    project_directory : str 
        Project that the trace plot should be added to.
        
    name: str
        The name of the trace plot displayed in SNUB and used
        for editing the config file. 
        
    traces: dict
        Dictionary mapping trace names to trace data. The data for each 
        trace should be a (N,2) array where the first column contains
        sorted time points (in seconds) and the second column contains
        the value of the trace at that timepoint.
        
    linewidth: int, default=1
        Linewidth used for plotting the traces

    trace_colors: dict, default={}
        To assign specific colors to any of the traces, use 
        ``trace_colors[name] = (r,g,b)``, where r,g,b are ints [0-255].
        
    bgcolor: (int,int,int), default=(0,0,0)
        Background color for the traceplot as ``(r,g,b)`` where r,g,b are ints [0-255].
        
    height_ratio: int, default=1
        The relative space initially allocated to this data-view in the track-stack. 
        Spacing can also be adjusted within the browser. 
        
    order: float, default=0
        Determines the order of placement within the track-stack.

    Returns
    -------
    props: dict
        trace plot properties
    """    
    
    # check that project exists and a trace plot with given name does not already exist
    config = load_config(project_directory)
    _confirm_no_existing_dataview(config, 'traceplot', name)
    
    # choose random colors for traces that werent assigned a color
    unassigned_traces = [k for k in traces.keys() if not k in trace_colors]
    print('Assigning random colors to traces',unassigned_traces)
    for k in unassigned_traces: trace_colors[k] = _random_color()
        
    # save traces
    data_path = name+'.trace_data.p'
    data_path_abs = os.path.join(project_directory,data_path)
    pickle.dump(traces, open(data_path_abs,'wb'))
    print('Saving trace plot data to '+data_path_abs)
        
    # add props to config
    props = {
        'name': name,
        'data_path': data_path,
        'linewidth': linewidth,
        'bgcolor': bgcolor,
        'trace_colors': trace_colors,
        'height_ratio': height_ratio,
        'order': order,
    }

    config['traceplot'].append(props)
    print('Added trace plot "{}\n" \n'.format(name,project_directory))
    save_config(project_directory, config)
    return props
    
   
    
def add_scatter(
    project_directory,
    name,
    xy_coordinates,
    time_intervals=None,
    binsize=None,
    start_time=None,
    features=None,
    feature_labels=None,
    colormap='viridis',
    xlim=None, 
    ylim=None, 
    pointsize=10, 
    linewidth=1, 
    facecolor=(180,180,180), 
    edgecolor=(0,0,0), 
    selected_edgecolor=(255,255,0),
    current_node_size=20, 
    current_node_color=(255,0,0),
    selection_intersection_threshold=0.5,
    size_ratio=1,
    order=0,
):
    """Add a scatter plot to your SNUB project.
    
    Parameters
    ----------
    project_directory : str 
        Project that the scatter plot should be added to.
        
    name: str
        The name of the scatter plot displayed in SNUB and used
        for editing the config file. 
        
    xy_coordinates : ndarray
        2D coordinates as a ``(N,2)`` array.
        
    time_intervals : ndarray, default=None
        Time interval (in seconds) associated with each point in the scatter
        plot, given as a ``(N,2)`` array with ``[start,end]`` in each
        row. If ``time_intervals=None``, then values for ``binsize``
        and ``start_time`` must be given. 

    binsize: float, default=None
        Uniform time interval (in seconds) associated with each point in the 
        scatter plot. It is assumed that the intervals have no gaps or overlaps. 
        If this is not the case, use the ``time_intervals`` argument. 
        
    start_time: float, default=None
        Start time (in seconds) of the earliest time interval associated
        with the scatter plot. ``start_time`` is used in conjunction with
        ``binsize`` to construct the time interval for each point. 
        
    features: ndarray, default=None
        Variables to use for coloring nodes in the scatter plot. ``features``
        should be a numpy array of shape (N,M) where N is the number of nodes
        and M is the number of features. ``feature_labels`` must be specified as well. 
        
    feature_labels: list(str), default=None
        Label corresponding to each column of ``features``.
        
    colormap: str, default='viridis'
        Colormap used for plotting `features` (must be one of the
        colormaps in matplotlib).
        
    xlim, ylim: [float, float], default=None
        Initial visible range of the scatter plot. If none is given, 
        the range will be determined automatically using pyqtgraph. 
        The visible range can be changed in the browser by panning
        and zooming. 
        
    pointsize: int, default=10
        Diameter of point in the scatter plot. 
        
    linewidth: int, default=1
        Width of the borderline on each point.
        
    facecolor: (int,int,int), default=(180,180,180)
        Color of points in the scatter plot.
        
    edgecolor: (int,int,int), default=(100,100,100)
        Edge color of points in the scatter plot when 
        they are not selected.
        
    selected_edgecolor: (int,int,int), default=(255,255,0)
        Edge color of points in the scatter plot when 
        they are selected.
        
    current_node_size: int, default=20
        If the current time overlaps with a point's time interval, the 
        point is highlighted by appearing larger and in another color. 
        ``current_node_size`` determines the diameter of the highlighted point.
        
    current_node_color: (int,int,int), default=(255,0,0)
        If the current time overlaps with a point's time interval, the 
        point is highlighted by appearing larger and in another color. 
        ``current_node_size`` determines the color of the highlighted point.
        
    selection_intersection_threshold: float, default=0.5
        When the current selection overlaps the interval associated with
        a point in the scatter plot, the point is highlighted.
        ``selection_intersection_threshold`` determines the amount of overlap
        required before the point is highlighted. A value of 1 means that
        the point's time interval must be fully covered.

    size_ratio: int, default=1
        The relative space initially allocated to this data-view in the panel-stack.
        Spacing can also be adjusted within the browser. 
        
    order: float, default=0
        Determines the order of placement within the panel-stack.
        Panels are arranged top-to-bottom (in column mode) or 
        left-to-right (row mode) by ascending rank of the ``order`` property.

    Returns
    -------
    props: dict
        scatter properties
    """    
    
    # check that project exists and a scatter plot with given name does not already exist
    config = load_config(project_directory)
    _confirm_no_existing_dataview(config, 'scatter', name)
    num_points = xy_coordinates.shape[0]
    
    # initialize time intervals
    if time_intervals is None: 
        if binsize is None or start_time is None:
            raise AssertionError(
                'Either a `time_intervals` must be given or `binsize` and `start_time` must be specified')
        time_intervals = generate_intervals(start_time, binsize, num_points)
        print('Initializing time intervals using start_time={} and binsize={}'.format(start_time, binsize))
    
    # initialize features:
    if features is None and feature_labels is None: features,feature_labels = np.zeros((num_points,0)),[]
    elif features is None or feature_labels is None: raise AssertionError('``features`` and ``feature_labels`` must both be specified')
    elif len(feature_labels) != features.shape[1]: raise AssertionError('The length of ``features_labels`` must match the number of columns in ``features``')
    elif features.shape[0] != num_points: raise AssertionError('``features`` must have the same number of rows as `xy_coordinates`')
    
    # save coordinatesm, time intervals and features
    data = np.hstack((xy_coordinates, time_intervals, features))
    data_path = name+'.scatter_data.npy'
    data_path_abs = os.path.join(project_directory,data_path)
    np.save(data_path_abs, data)
    print('Saving scatter plot data to '+data_path_abs)
        
    # add props to config
    props = {
        'name': name,
        'data_path': data_path,
        'pointsize': pointsize,
        'linewidth': linewidth,
        'facecolor': facecolor,
        'edgecolor': edgecolor,
        'colormap': colormap,
        'feature_labels':feature_labels,
        'selected_edgecolor': selected_edgecolor,
        'current_node_size': current_node_size,
        'current_node_color': current_node_color,
        'selection_intersection_threshold': selection_intersection_threshold,
        'size_ratio': size_ratio,
        'order': order,
    }
    if xlim is not None: props['xlim'] = xlim
    if ylim is not None: props['ylim'] = ylim
    
    config['scatter'].append(props)
    print('Added scatter plot "{}" \n'.format(name))
    save_config(project_directory, config)
    return props
    
    

def add_heatmap(
    project_directory,
    name,
    data,
    time_intervals=None,
    binsize=None,
    start_time=None,
    sort_method=None,
    labels=None,
    show_labels=False,
    max_label_width=300, 
    label_color=(255,255,255),
    label_font_size=12, 
    colormap='viridis', 
    vmin=None, vmax=None,
    add_traceplot=True,
    height_ratio=1,
    trace_height_ratio=1,
    heatmap_height_ratio=2,
    order=0,
):
    
    """Add a heatmap to your SNUB project.
    If plotting neural data, it is helpful to sort the rows of the heatmap
    so that correlated neurons are clustered together (use the ``sort_method``
    argument; see :py:func:`snub.io.manifold.sort` for options).
    
    
    Parameters
    ----------
    project_directory : str 
        Project that the heatmap should be added to.
        
    name: str
        The name of the heatmap displayed in SNUB and used
        for editing the config file. 
        
    data : ndarray
        2D array where rows are variables and columns are time bins.

    time_intervals : ndarray, default=None
        Time interval (in seconds) associated with each column of the heatmap, 
        given as a ``(N,2)`` array with ``[start,end]`` in each
        row. If ``time_intervals=None``, then values for ``binsize``
        and ``start_time`` must be given. 

    binsize: float, default=None
        Uniform time interval (in seconds) associated with each column of the
        heatmap. It is assumed that the intervals have no gaps or overlaps. 
        If this is not the case, use the ``time_intervals`` argument. 
        
    start_time: float, default=None
        Start time (in seconds) of the earliest time interval in the
        heatmap. ``start_time`` is used in conjunction with
        ``binsize`` to construct the time interval for each column.
        
        
    sort_method: str/ndarray, default=None
        Method for sorting the rows of the heatmap. ``sort_method`` can 
        either be an array directly specifying the row order or a str
        defining a sort method from :py:func:`snub.io.manifold.sort`.
        If ``sort_method=None``, the original ordering of the rows will be used.
        
    labels: list of str, default=None
        Labels for each variable (row) in the heatmap. If ``show_labels=True``,
        the labels are rendered within SNUB. If ``add_traceplot=True``, the 
        labels are also used to plot specific variables in the trace plot
        associated with the heatmap. When no labels are given, they
        default to the integer order of each row. If the elements of ``labels``
        are not unique, their integer order is prepended. 
        
    show_labels: bool, default=False
        Determines whether labels are rendered on the left side of the heatmap
        in SNUB. It is recommended to leave ``show_labels=False`` when the heatmap
        contains a large number of rows. 
        
    max_label_width: int, default=300
        If ``show_labels=True``, ``max_label_width`` determines how far
        the label text can encroach on the heatmap (in pixels). This 
        is only relevant if any of the labels are really long. 
    
    label_color: (int,int,int), default=(255,255,255)
        Color of the labels superimposed on the heatmap if ``show_labels=True``. 
    
    label_font_size: int, default=12
        Size of the labels superimposed on the heatmap if ``show_labels=True``. 
    
    colormap: str, default='viridis'
        Colormap used for rendering the heatmap values. The colormap
        options are ported from matplotlib via `cmapy <https://gitlab.com/cvejarano-oss/cmapy/>`_
        
    vmin: float, default=None
        Floor for the colormap. If ``vmin=None``, it will be set to to the 1st percentile
        of the data values. This parameter can be adjusted within the browser.
    
    vmax: float, default=None
        Ceiling for the colormap. If ``vmax=None``, it will be set to to the 99th percentile
        of the data values. This parameter can be adjusted within the browser.
    
    add_traceplot: bool, default=True
        Determines whether or not a trace plot is added with the heatmap.
        This is useful for pulling out and plotting specific rows from the heatmap.

    height_ratio: int, default=1
        The relative height initially allocated to this data-view in the track-stack.
        Spacing can also be adjusted within the browser. 
        
    trace_height_ratio: int, default=1
        If ``add_traceplot=True``, this parameter determines the relative height
        initially allocated to the trace plot associated with the heatmap.
        Spacing can also be adjusted within the browser. 
        
    heatmap_height_ratio: int, default=2
        If ``add_traceplot=True``, this parameter determines the relative height
        initially allocated to the heatmap compared to its associated trace plot.
        Spacing can also be adjusted within the browser. 
        
    order: float, default=0
        Determines the order of placement within the track-stack.
        
    Returns
    -------
    props: dict
        heatmap properties
    """    
    
    # check that project exists and a heatmap with the given name does not already exist
    config = load_config(project_directory)
    _confirm_no_existing_dataview(config, 'heatmap', name)
    
    # save heatmap data
    data_path = name+'.heatmap_data.npy'
    data_path_abs = os.path.join(project_directory,data_path)
    np.save(data_path_abs, data)
    print('Saved heatmap data to '+data_path_abs)

    # initialize/save time intervals
    if time_intervals is None: 
        if binsize is None or start_time is None:
            raise AssertionError(
                'Either a `time_intervals` must be given or `binsize` and `start_time` must be specified')
        time_intervals = generate_intervals(start_time, binsize, data.shape[1])
        print('Initializing time intervals using start_time={} and binsize={}'.format(start_time, binsize))
    
    intervals_path = name+'.heatmap_intervals.npy'
    intervals_path_abs = os.path.join(project_directory,intervals_path)
    np.save(intervals_path_abs, time_intervals)
    print('Saved time intervals to '+intervals_path_abs)

    # save labels
    if labels is None: 
        labels = [str(i) for i in range(data.shape[0])]
        print('Creating labels from row ordering')
    elif len(labels) != data.shape[0]:
        raise AssertionError(
            'The length of `labels` ({}) does not match the number of rows in the heatmap ({})'.format(len(labels), data.shape[0]))
    elif len(set(labels)) < len(labels):
        print('labels are not unique: prepending integers')
        labels = [str(i)+':'+l for i,l in enumerate(labels)]
        
    labels_path = name+'.heatmap_labels.txt'
    labels_path_abs = os.path.join(project_directory,labels_path)
    open(labels_path_abs,'w').write('\n'.join(labels))
    print('Saved labels to '+labels_path_abs)
    
    # save row order
    if sort_method is None:
        row_order = np.arange(data.shape[0])
    if isinstance(sort_method, str):
        from snub.io.manifold import sort
        row_order = sort(data, method=sort_method)
    else:
        try: data[sort_method]
        except: raise AssertionError(
            '`sort_order` must be None, a string, or a valid index that can be used in `data[sort_method]`')
    row_order_path = name+'.heatmap_row_order.npy'
    row_order_path_abs = os.path.join(project_directory,row_order_path)
    np.save(row_order_path_abs, row_order)
    print('Saved row order to '+row_order_path_abs)
        
    # check that the colormap is valid
    import cmapy
    try: cmapy.cmap(colormap)
    except: raise AssertionError(
        '""{}"" is not a valid colormap. See https://matplotlib.org/stable/gallery/color/colormap_reference.html for a list of options'.format(colormap))
        
    if vmin is None: 
        vmin = np.percentile(data.flatten(),1)
        print('Set vmin to {}'.format(vmin))
    if vmax is None: 
        vmax = np.percentile(data.flatten(),99)
        print('Set vmax to {}'.format(vmax))
        
    # add props to config
    props = {
        'name': name,
        'data_path': data_path,
        'intervals_path':intervals_path,
        'labels_path': labels_path,
        'show_labels': show_labels,
        'row_order_path': row_order_path,
        'max_label_width': max_label_width,
        'label_color': label_color,
        'label_font_size':label_font_size,
        'colormap':colormap,
        'vmin':vmin,
        'vmax':vmax,
        'add_traceplot':add_traceplot,
        'height_ratio': height_ratio,
        'heatmap_height_ratio':heatmap_height_ratio,
        'trace_height_ratio':trace_height_ratio,
        'order': order,
    }
    config['heatmap'].append(props)
    print('Added heatmap "{}"\n'.format(name))
    save_config(project_directory, config)
    return props
    
    
def add_spikeplot(
    project_directory,
    name,
    spike_times, 
    spike_labels,
    heatmap_range=60,
    window_size=0.2,
    window_step=0.02,
    labels=None,
    sort_method=None,
    show_labels=False,
    max_label_width=300, 
    label_color=(255,255,255),
    label_font_size=12, 
    colormap='viridis', 
    vmin=None, vmax=None,
    add_traceplot=True,
    height_ratio=1,
    trace_height_ratio=1,
    heatmap_height_ratio=2,
    order=0,
):   
    """Add a spike plot to your SNUB project.
    By default, spike plots convert to heatmaps when sufficiently zoomed out.
    For electrophysiology, this corresponds to showing firing *rates* as
    opposed to firing *events* (see :py:func:`snub.io.manifold.firing_rates`).
    Most of the options for :py:func:`snub.io.project.add_heatmap` 
    can also be used here. 
    
    If plotting neural data, it is helpful to sort the rows
    so that correlated neurons are clustered together (use the ``sort_method``
    argument; see :py:func:`snub.io.manifold.sort` for options; the firing
    rates are used for sorting).
    
    Parameters
    ----------
    project_directory : str 
        Project that the spike plot should be added to.
        
    name: str
        The name of the spike plot displayed in SNUB and used
        for editing the config file. 
        
    spike_times : ndarray
        Spike times (in seconds) for all units. The source of each spike is
        input separately using ``spike_labels``
        
    spike_labels: ndarray
        The source/label for each spike in ``spike_times``. The maximum
        value of this array determines the number of rows in the heatmap.
        
    heatmap_range: float, default=60
        Defines the zoom-level at which the spike-view converts to
        a heatmap-view. The transition occurs when the currently
        visible range in the timeline is equal to ``heatmap_range`` (in seconds)
        
    window_size: float, default=0.2
        Length (in seconds) of the sliding window used to calculate firing rates
        
    window_step: float, default=0.02
        Step-size (in seconds) between each window used to calculate firing rates
        
    Returns
    -------
    props: dict
        spikeplot properties

    """ 
    # check that project exists and a spike plot with the given name does not already exist
    config = load_config(project_directory)
    _confirm_no_existing_dataview(config, 'spikeplot', name)
    
    # save spike times and spike labels
    spike_labels = spike_labels.astype(int)
    spike_data = np.vstack((spike_times, spike_labels)).T
    spikes_path = name+'.spikeplot_spikes.npy'
    spikes_path_abs = os.path.join(project_directory,spikes_path)
    np.save(spikes_path_abs, spike_data)
    print('Saved spike data to '+spikes_path_abs)
    
    # save heatmap
    from snub.io.manifold import firing_rates
    heatmap_data, start_time = firing_rates(spike_times, spike_labels, window_size=window_size, window_step=window_step)
    heatmap_path = name+'.spikeplot_heatmap.npy'
    heatmap_path_abs = os.path.join(project_directory,heatmap_path)
    np.save(heatmap_path_abs, heatmap_data)
    print('Saved firing rate data to '+heatmap_path_abs)

    # save time intervals
    time_intervals = generate_intervals(start_time, window_step, heatmap_data.shape[1])
    intervals_path = name+'.spikeplot_intervals.npy'
    intervals_path_abs = os.path.join(project_directory,intervals_path)
    np.save(intervals_path_abs, time_intervals)
    print('Saved time intervals to '+intervals_path_abs)

    
    # save labels
    if labels is None: 
        labels = [str(i) for i in range(heatmap_data.shape[0])]
        print('Creating labels from row ordering')
    elif len(labels) != heatmap_data.shape[0]:
        raise AssertionError(
            'The length of `labels` ({}) does not match the number of arrays in `spike_times` ({})'.format(len(labels), heatmap_data.shape[0]))
    elif len(set(labels)) < len(labels):
        print('labels are not unique: prepending integers')
        labels = [str(i)+':'+l for i,l in enumerate(labels)]
    
    labels_path = name+'.spikeplot_labels.txt'
    labels_path_abs = os.path.join(project_directory,labels_path)
    open(labels_path_abs,'w').write('\n'.join(labels))
    print('Saved labels to '+labels_path_abs)
 
    # save row order
    if sort_method is None:
        row_order = np.arange(heatmap_data.shape[0])
    elif isinstance(sort_method, str):
        from snub.io.manifold import sort
        row_order = sort(heatmap_data, method=sort_method)
    else:
        row_order = sort_method.astype(int)
        try: heatmap_data[row_order]
        except: raise AssertionError(
            '`sort_order` must be None, a string, or a valid index that can be used in `data[sort_method]`')
    row_order_path = name+'.spikeplot_row_order.npy'
    row_order_path_abs = os.path.join(project_directory,row_order_path)
    np.save(row_order_path_abs, row_order)
    print('Saved row order to '+row_order_path_abs)
        
    # check that the colormap is valid
    import cmapy
    try: cmapy.cmap(colormap)
    except: raise AssertionError(
        '""{}"" is not a valid colormap. See https://matplotlib.org/stable/gallery/color/colormap_reference.html for a list of options'.format(colormap))

    if vmin is None: 
        vmin = np.percentile(heatmap_data.flatten(),1)
        print('Set vmin for heatmap to {}'.format(vmin))
    if vmax is None: 
        vmax = np.percentile(heatmap_data.flatten(),99)
        print('Set vmax for heatmap to {}'.format(vmax))
        
    # add props to config
    props = {
        'name': name,
        'heatmap_path': heatmap_path,
        'spikes_path': spikes_path,
        'intervals_path':intervals_path,
        'labels_path': labels_path,
        'row_order_path': row_order_path,
        'show_labels': show_labels,
        'max_label_width': max_label_width,
        'label_color': label_color,
        'label_font_size':label_font_size,
        'heatmap_range':heatmap_range,
        'colormap':colormap,
        'vmin':vmin,
        'vmax':vmax,
        'add_traceplot':add_traceplot,
        'height_ratio': height_ratio,
        'heatmap_height_ratio':heatmap_height_ratio,
        'trace_height_ratio':trace_height_ratio,
        'order': order,
    }
    config['spikeplot'].append(props)
    print('Added spike plot "{}"\n'.format(name))
    save_config(project_directory, config)
    return props
    


def add_mesh():
    """None implemented
    """
    
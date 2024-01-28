Neurodata Without Borders
=========================

We provide a rudimentary tool for automatically generating a SNUB project from NWB files, which contain raw and processed data from neuroscience recordings. The data are stored hierarchically, and each component of the hierarchy has a specific neurodata type that reflects the measurement modality (e.g ``Units`` for spike trains, ``ImageSeries`` for video, etc.). Our conversion tool generates a SNUB subplot for each supported neurodata type. Users can optionally restrict this process to a subset of the NWB hierarchy (e.g. include pose tracking while excluding electrophysiology, or include just a subset of electrophysiology measurements). 


Neurodata types
---------------

The following neurodata types are supported:

- ``IntervalSeries``
    Contains start and end times for (possibly labeled) intervals. A SNUB trace plot is generated containing one trace per interval type.

- ``RoiResponseSeries``
    Contains fluorescence traces for regions of interest (ROIs). A SNUB heatmap is generated containing one row per ROI. Metadata associated with each ROI is not linked in the SNUB plot.

- ``TimeSeries``
    Contains time series in one or more dimensions. A SNUB heatmap is generated for 15 or more dimensions, and a SNUB trace plot is generaed for fewer than 15 dimensions.

- ``PoseEstimation``
    Contains pose tracking data (available via the ``ndx-pose`` extension). A SNUB trace plot is generated for each tracked body part and spatial dimension. For 3D data, a 3D pose plot is also generated.

- ``ImageSeries``
    Contains video data. We assume that the video is stored as a separate file and that the ``ImageSeries`` object contains frame timestamps and a relative path to that file. A SNUB video plot is then generated.

- ``LabelSeries``
    Contains discrete label time series in the form of a binary matrix with one column per label abd one row per time bin (available via the ``ndx-labels`` extension). A SNUB heatmap is generated directly from this matrix.

- ``TimeIntervals``
    Contains annotated intervals. Each interval has a start time, a stop time, and an arbitrary number of additional metadata fields. A SNUB trace plot is generated with one trace showing the start and stop times of each interval. All other metadata is ignored since it cannot be canonically represented using the currently available SNUB plot types.

- ``Position``
    Contains position data in the form of one or more ``SpatialSeries`` objects. A SNUB trace plot is generated with traces for each spatial dimensions of each consistuent spatial series.

- ``SpatialSeries``
    Contains spatial data in the form of a time series with one or more dimensions. A standalone SNUB trace plot is generated for the spatial series if it is not contained within a ``Position`` object.

- ``Units``
    Contains spike trains for one or more units. A corresponding SNUB spike plot is generated.

- ``Events``
    Contains a sequence of unlabeled event times (available via the ``ndx-events`` extension). A SNUB trace plot is generated with a single trace that spikes at each event time.


Examples
--------

For each example, run the first code block in a terminal and the second in a python console or notebook.


A change in behavioral state switches the pattern of motor output that underlies rhythmic head and orofacial movements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Liao, Song-Mao; Kleinfeld, David; Rinehart, Duane; University of California San Diego (2023) Dataset for: A change in behavioral state switches the pattern of motor output that underlies rhythmic head and orofacial movements (Version 0.230515.0530) [Data set]. DANDI archive. https://doi.org/10.48324/dandi.000540/0.230515.0530*

Includes the following SNUB-compatible neurodata types: ``TimeSeries``, ``ImageSeries``

  .. code-block:: bash

    # Download NWB file
    dandi download https://api.dandiarchive.org/api/dandisets/000540/versions/0.230515.0530/assets/94307bee-459c-424e-b3a0-1e86b23f04b2/download/

    # Download associated video and create directory for it
    dandi download https://api.dandiarchive.org/api/dandisets/000540/versions/0.230515.0530/assets/942b0806-2c8b-4289-a072-9e965884fcb6/download/
    mkdir sub-SLR087_ses-20180706_obj-14ua2bs_behavior+image
    mv 9557b48e-46f0-45f2-a700-a2e15318c5bc_external_file_0.avi sub-SLR087_ses-20180706_obj-14ua2bs_behavior+image/


  .. code-block:: python

    import os, snub

    # Define paths
    nwb_file = "sub-SLR087_ses-20180706_obj-14ua2bs_behavior+image.nwb"
    name = os.path.splitext(os.path.basename(nwb_file))[0]
    project_directory = os.path.join(os.path.dirname(nwb_file), f"SNUB-{name}")

    # Make SNUB plot that includes video and torso tracking
    snub.io.create_project_from_nwb(project_directory, nwb_file, branches=['torso_dlc', 'ImageSeries'])


A Unified Framework for Dopamine Signals across Timescales
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Kim, HyungGoo; Malik, Athar; Mikhael, John; Bech, Pol; Tsutsui-Kimura, Iku; Sun, Fangmiao; Zhang, Yajun; Li, Yulong; Watabe-Uchida, Mitsuko; Gershman, Samuel; Uchida, Naoshige (2023) A Unified Framework for Dopamine Signals across Timescales (Version draft) [Data set]. DANDI archive. https://dandiarchive.org/dandiset/000251/draft*

Includes the following SNUB-compatible neurodata types: ``TimeSeries``, ``TimeIntervals``, ``SpatialSeries``, ``Events``

  .. code-block:: bash

    # Download NWB file
    dandi download https://api.dandiarchive.org/api/dandisets/000251/versions/draft/assets/b28fcb84-2e23-472c-913c-383151bc58ef/download/


  .. code-block:: python

    import os, snub

    # Define paths
    nwb_file = "sub-108_ses-Ca-VS-VR-2.nwb"
    name = os.path.splitext(os.path.basename(nwb_file))[0]
    project_directory = os.path.join(os.path.dirname(nwb_file), f"SNUB-{name}")

    # Make SNUB plot
    snub.io.create_project_from_nwb(project_directory, nwb_file)


Neural population dynamics during reaching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Churchland, Mark; Cunningham, John P.; Kaufman, Matthew T.; Foster, Justin D.; Nuyujukian, Paul; Ryu, Stephen I.; Shenoy, Krishna V. (2022) Neural population dynamics during reaching (Version draft) [Data set]. DANDI archive. https://dandiarchive.org/dandiset/000070/draft*

Includes the following SNUB-compatible neurodata types: ``Units``, ``TimeIntervals``, ``Position``

  .. code-block:: bash
      
    # Download NWB file
    dandi download https://api.dandiarchive.org/api/dandisets/000070/versions/draft/assets/7b95fe3a-c859-4406-b80d-e50bad775d01/download/

  .. code-block:: python

    import os, snub
    
    # Define paths
    nwb_file = "sub-Jenkins_ses-20090912_behavior+ecephys.nwb"
    name = os.path.splitext(os.path.basename(nwb_file))[0]
    project_directory = os.path.join(os.path.dirname(nwb_file), f"SNUB-{name}")

    # Make SNUB plot
    snub.io.create_project_from_nwb(project_directory, nwb_file)

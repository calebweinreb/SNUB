# Systems Neuro Browser (SNUB)

[![DOI](https://joss.theoj.org/papers/10.21105/joss.06187/status.svg)](https://doi.org/10.21105/joss.06187)

## [Read the documentation!](https://snub.readthedocs.io/en/latest/)

SNUB is a visual interface for systems neuroscience. Using a set of linked data-views, users can explore relationships between raw video, 3D animal pose, behavior annotations, neural activity, or any other relevant time-series data.

![](https://github.com/calebweinreb/SNUB/blob/main/docs/media/use_case1.gif)


## Installation

Create and activate a new conda environment with python≥3.8 and install via pip
```
conda create -n snub python=3.8
conda activate snub
pip install systems-neuro-browser
```
To speed up selections, `pip install ncls`. To install optional developer dependencies, `pip install systems-neuro-browser[dev]`. The docs include more detailed [installation instructions](https://snub.readthedocs.io/en/latest/install.html).

## Getting Started

* Download the [example project](https://zenodo.org/records/10578025/files/miniscope_project.zip?download=1). 
* Launch SNUB from the command line with the command `snub`.
* Go to `File > Open Project`, navigate to the project directory, and hit `Choose` with the directory selected.
* Alternatively, launch SNUB directly with the project path `snub /path/to/project/directory`.
   
## Browse your own data

Loading data is simple with the `snub.io` module. For example the following code creates a new project with paired electrophysiology and video data. See the [Tutorial](https://snub.readthedocs.io/en/latest/tutorials.html) for more details. 

```
import snub.io

project_directory = 'path/to/new/project'

snub.io.project.create_project(project_directory, duration=1800)
snub.io.project.add_video(project_directory, 'path/to/my_video.avi', name='IR_camera')
snub.io.project.add_splikeplot(project_directory, 'my_ephys_data', spike_times, spike_labels) 
```

## Convert an NWB file

We provide a rudimentary tool for automatically generating SNUB datasets from Neurodata Without Borders (NWB) files, which contain raw and processed data from neuroscience recordings. The data in NWB files are stored hierarchically, and each component of the hierarchy has a specific neurodata type that reflects the measurement modality (e.g, "Units" for spike trains, "ImageSeries" for video). Our conversion tool generates a SNUB display element for each supported neurodata type. Users can optionally restrict this process to a subset of the NWB hierarchy (e.g., include pose tracking while excluding electrophysiology, or include just a subset of electrophysiology measurements). Here's an example:

```
# Run from the command line

# Download NWB file
dandi download https://api.dandiarchive.org/api/dandisets/000540/versions/0.230515.0530/assets/94307bee-459c-424e-b3a0-1e86b23f04b2/download/

# Download associated video and create directory for it
dandi download https://api.dandiarchive.org/api/dandisets/000540/versions/0.230515.0530/assets/942b0806-2c8b-4289-a072-9e965884fcb6/download/
mkdir sub-SLR087_ses-20180706_obj-14ua2bs_behavior+image
mv 9557b48e-46f0-45f2-a700-a2e15318c5bc_external_file_0.avi sub-SLR087_ses-20180706_obj-14ua2bs_behavior+image/
```

```
# Run in python

import os, snub

# Define paths
nwb_file = "sub-SLR087_ses-20180706_obj-14ua2bs_behavior+image.nwb"
name = os.path.splitext(os.path.basename(nwb_file))[0]
project_directory = os.path.join(os.path.dirname(nwb_file), f"SNUB-{name}")

# Make SNUB plot that includes video and torso tracking
snub.io.create_project_from_nwb(project_directory, nwb_file, branches=['torso_dlc', 'ImageSeries'])
```
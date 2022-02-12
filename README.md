# SNUB (Systems Neuro Browser)

## [Read the documentation!](https://snub.readthedocs.io/en/latest/)

SNUB is a visual interface for systems neuroscience. Using a set of linked data-views, users can explore relationships between raw video, 3D animal pose, behavior annotations, neural activity, or any other relevant time-series data.

![](https://github.com/calebweinreb/SNUB/blob/main/docs/media/use_case1.gif)


## Installation

Create and activate a new conda environment with python≥3.8, clone this repo, and install via pip
```
conda create -n snub python=3.8
conda activate snub
git clone https://github.com/calebweinreb/SNUB.git
pip install -e SNUB
```
To speed up selections, `pip install ncls`. To use the 3D mesh viewer, install `pip install PyOpenGL PyOpenGL_accelerate`. The docs include more detailed [installation instructions](https://snub.readthedocs.io/en/latest/install.html).

## Getting Started

* Download the [example project](https://www.dropbox.com/sh/ujr3ttdc3gsxtqt/AAAKLL9iaF54cOwPKRPMTENIa?dl=0). 
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

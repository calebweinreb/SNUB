---
title: 'Systems Neuro Browser (SNUB)'
tags:
  - Python
  - neuroscience
  - animal behavior
  - graphical user interface
authors:
  - name: Caleb Weinreb
    orcid: 0000-0001-6100-6084
    affiliation: 1
  - name: Sandeep Robert Datta
    orcid: 0000-0002-8068-3862
    affiliation: 1
affiliations:
 - name: Department of Neurobiology, Harvard University, Boston, MA
   index: 1
date: 5 October 2022
bibliography: paper.bib

---

# Summary

SNUB is a tool for exploring time-series data, such as neural 
recordings, behavioral videos, temperature, movement or other sensor signals, 
and any higher-level annotations derived from such data. The interface is 
divided into windows that each show a different data stream and all synchonize 
to a common timeline. The linked data views allow users to quickly inspect 
the relationships between different phenomena, such as the behaviors that 
occur during a particular pattern of neural activity (\autoref{fig:screenshot}). 

![Screenshot from SNUB.\label{fig:screenshot}](docs/media/screenshot.png)

We provide dedicated widgets and loading functions for exploring
raw video, 3D animal pose, behavior annotations, electrophysiology recordings,
and calcium imaging data - either as a raster or as a super-position of 
labeled regions of interest (ROIs). More broadly, SNUB can dislay any data
that takes the form of a heatmap, scatter plot, video, or collection of 
named temporally-varying signals. 

In addition to the front-end GUI, we include a library of functions for
ingesting raw data and saving it to a format that is readable by the SNUB
viewer. The following code, for example, creates a project with paired 
electrophysiology and video data.

```
snub.io.create_project(project_directory, duration=1800)
snub.io.add_video(project_directory, 'path/to/my_video.avi', name='IR_camera')
snub.io.add_splikeplot(project_directory, 'my_ephys_data', spike_times, spike_labels)
```

SNUB is a flexible general-purpose tool that complements more specialized 
packages such as rastermap [@rastermap] or Bento [@bento]. The rastermap user 
interface, for example, is hard-coded for the display of neural activity 
rasters, ROIs and 2D embeddings of neural activity. Bento is hard-coded for 
the display of neural activity rasters, behavioral videos and behavioral 
annotations. SNUB can reproduce either of these configurations and is 
especially useful when one wishes to include additional types of data
or more directly customize the way that data is rendered.

The graphics in SNUB are powered by vispy [@vispy]. SNUB includes wrappers
for several dimensionality reduction methods, including rastermap [@rastermap]
for ordering raster plots and UMAP [@umap] for 2D scatter plots. Fast video
loading is enabled by vidio [@vidio].

# Acknowledgements

We are grateful to Mohammed Osman for initial contributions to the 3D keypoint
visualization tool. CW is a Fellow of The Jane Coffin Childs Memorial Fund for 
Medical Research. SRD ... 

# References
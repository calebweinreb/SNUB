# SNUB (systems neuro browser)

![](https://github.com/calebweinreb/SNUB/blob/main/docs/screen_capture.gif)


## Installation
Create a new environment, clone this repo and pop install
```
conda create -n snub python=3.7
git clone https://github.com/calebweinreb/SNUB.git
pip instal -e snub
```

## Quick start
With the installation conda environment loaded, run
`snub [path/to/snub/repo]/projects/example_1p_imaging_and_location`
- Overall controls
  - Use the play/pause button at the bottom to playback data in real-time
- Video controls
  - On a mac track-pad, use multi-touch gestures to zoom/pan around the video view
- Rasters/timeline controls:
  - Click and/or drag to change the current frame
  - On a mac track-pad, two-finger-swipe up-and-down to zoom in and out
  - On a mac track-pad, two-finger-swipe sideways to pan through time
  - Shift-click-and-drag to select frames, or control-click-and-drag to deselect
  - With frames selected, right-click for the option to re-order the raster mean value in the selected region

## TODO
- [ ] Document project directory format
- [ ] Code documentation / docstrings
- [ ] Show other time units in timeline
- [ ] Test non-trackpad interaction
- [ ] Test non-MacOS operating systems
- [ ] Add support for spike data
- [ ] Add line-graph viewer

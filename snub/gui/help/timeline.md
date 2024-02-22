## Timeline

SNUB always shows a timeline on the bottom of the window. All data-views that have time as a dimension (such as [heatmaps](heatmaps.md) or [trace plots](trace_plots.md)) are aligned to the timeline, which indicates the currently visible time interval. SNUB also maintains a "current time" that determines e.g. which frame is shown in the [video player](video.md) or which point in a [scatter plot](scatter_plots.md) is highlighted. The current time is indicated by a vertical line in the timeline. If the current time is outside the interval of the timeline, this line is not shown.

### Navigation

* Use scrolls/gestures to change the currently visible time interval.
* Click on the timeline to set the current time.
* Use the play button and speed slider at the bottom of the window to animate the current time.
* Turn on "center playhead" to make the currently visible time interval be centered on the current time.
* Toggle the timeline unit between minutes:seconds and "timestemps". Timesteps are multiples of the "min_step" parameter that went into the construction of the current SNUB project. These discrete timesteps can be useful for accessing specific timepoinmts (e.g. video frames) outside of SNUB.


**Note: If playback is not smooth, try minimizing some of the visible panels (using the minus sign in the top right of each panel). Panels can be permanently removed by clicking the "x" in the top right of the panel.**
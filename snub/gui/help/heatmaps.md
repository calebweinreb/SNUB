## Heatmaps

Heatmaps dispay time-series data using color intensity (one time-series per row). They are aligned to the [timeline](timeline.md) at the bottom of the window and can be navigated using gestures (pan and zoom).

* **To adjust the colormap**, right click on the heatmap and select "Adjust colormap range" and enter a new min or max value.
* **For vertical zoom**, right click on the heatmap and select "Zoom in (vertical)" or "Zoom out (vertical)". Zooming is centered in the point where you clicked. We do not provide a direct way to scroll along the vertical axis, so if you are zoomed in the top rows of the heatmap and want to see the bottom rows, you will need to zoom out from the top rows and then zoom back in to the bottom rows.
* **To highlight a row label**, hover over the column of labels on the left side of the heatmap and click on the label. The label currently under the mouse will enlarge.
* **To show/hide row labels**, right click on the heatmap and select "Hide row labels" or "Show row labels:.


### Plotting specific rows

By default, when a heatmap is added to a SNUB project it is paired with a [trace plot](trace_plots.md). The trace plot contains a copy of each row of the heatmap and can be used to plot the time-series data for specific rows. There are two ways to plot the data for a given row:

* Right click on the heatmap (over the row of interest) and select "Plot trace".
* Hover over the row label on the left side of the heatmap (so it becomes enlarged) and click.

### Additional topics

See [Selections](selections.md) for how to reorder the rows of the heatmap by their enrichment in a selection of time intervals.
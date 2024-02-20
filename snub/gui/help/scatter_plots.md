## Scatter plots

Scatter plots display two-dimensional data using points. In SNUB, each point corresponds to a time interval, and may also be associated with a value for one or more variables (e.g. the current speed of the animal). These variables (which are listed in a menu on the left) can be used to color the points.

* **To show/hide the variable menu**, click the drop-down menu in the top right corner and click "Show/hide variable menu". The divider between the variable menu and the scatter plot can also be dragged to adjust the width of the menu.
* **To adjust the colormap**, right click on the scatter plot and select "Adjust colormap range" and enter a new min or max value.
* **To reorder points by the current variable**, right click on the scatter plot and ensure that "Plot high values on top" is checked. This is useful when a variable is very sparse and you want to see the points with the highest values.
* **To change the radius and border width of the markers**, right click on the scatter plot and select "Adjust marker appearance".

### Visualizing dynamics

The whenever the current time (as indicated by the vertical line in the [timeline](timeline.md)) falls within the interval of a point in the scatter plot, the point is highlighted with a big red dot. In some cases, it may also be useful to visulize temporal trajectories in the scatter plot. This can be done using a "marker trail", which uses red dots of decreasing radius to highlight markers that consecutively precede the current time. 

* **To show/hide the marker trail**, right click on the scatter plot and select "Show/hide marker trail". Note that you may need to play/scrub the timeline to see the trail initially.

### Additional topics

See [Selections](selections.md) for how to select points in the scatter plot and rank variables by their enrichment in the selection.
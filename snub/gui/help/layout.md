## Layout

The SNUB layout is organized hierarchically: each project is a tab, and each tab contains multiple data-views. 

* **To add a new tab**, [load a project](loading_data.md) using the "File" menu. 
* **To remove a tab**, click the "x" in the top right corner of the tab.
* **To remove a data-view**, either minimize it using the minus sign in the top right corner or click the "x" in the top right corner. Minizing is temporary, whereas clicking the "x" is permanent. Removing/minimizing data-views can help improve performance, especially during playback.
* **To change data-view sizes**, drag the corresponding dividers (all dividers are draggable).

### Track and panel stacks

The layout is divided into two sections: a "panel stack" (left) and a "track stack" (right). The track stack contains the the [timeline](timeline.md) and all data-views that have time as a dimension, such as [heatmaps](heatmaps.md) and [trace plots](trace_plots.md). The panel stack contains all the data-views change over time, but don't have time as an explicit spatial dimension, such as [scatter plots](scatter_plots.md) and [video players](video.md). By default, these two components are arrayed horizontally, and their inner components are arrayed vertically.

* **To move the panel stack above the track stack**, go to Window > Layout and check "Rows". This will also cause the panels in the panel stack to be arrayed horizontally.
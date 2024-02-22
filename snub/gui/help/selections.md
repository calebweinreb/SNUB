## Selecting and deselecting

Selections can be used to show relationships between data-views (such intervals on the [timeline](timeline.md) that correspond to a subset of points in a [scatter plot](scatter_plots.md)), or to identify variables that are enriched in a subset of the data.

* Use shift+drag to select points in the scatter view or intervals in the timeline.
* Use command/control+drag to deselect points and intervals.
* Use Edit > Deselect All to deselect everything

## Rank variables by enrichment

### Scatter plot

 [Scatter plots](scatter_plots.md) may include user-defined variables that vary between points. By default, these variables are listed in a menu on the left side of the scatter plot. Ranking by enrichment helps identify variables that are particularly high in a subset of points. To perform this analysis:

* Select a subset of points
* Right-click on the scatter plot to open the context menu
* Click "Rank by enrichment"
* The variable menu will reorder to show the most enriched variables at the top
* To return to the default ordering, right-click and select "Restore original variable order"

*Note: Enrichment is calculated by Z-scoring each variable and then taking the mean Z-score for the selected points.*

### Heatmap

To identify rows of a [heatmap](heatmaps.md) that are enriched in a subset of the timeline:

* Select one or more intervals on the timeline
* Right-click on the heatmap to open the context menu
* Click "Reorder by selection" (this may take a few seconds)
* The heatmap will reorder to show the most enriched rows at the top
* To return to the default ordering, right-click and select "Restore original order"

*Note: Enrichment is calculated by Z-scoring each row and then taking the mean Z-score for the selected intervals.*
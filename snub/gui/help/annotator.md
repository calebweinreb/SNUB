## Annotation

The annotator widget can be used to define intervals when particular events happen. The widget is initialized with set of labels and is divided into rows (one for each label). 

* Use shift+drag within a row to add an interval
* Use command/control+drag within a row to subtract an interval

### Saving and loading annotations

Annotations are stored as a list of intervals (start and end times in seconds) for each label. By default, the current state of the widget is automatically saved to a file within the SNUB project whenever a change is made. This file can be accessed directly, or a copy of the annotations can be exported in json format using the context menu. Annotations can also be imported from elsewhere in the same format.

* Right-click on the annotator widget to open the context menu
* Click on the checkbox to toggle automatic saving
* Click Import or Export to load or save the current annotations
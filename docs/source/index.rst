SNUB (Systems Neuro Browser)
============================

`Github Repository <https://github.com/calebweinreb/SNUB>`_

.. image:: ../media/use_case1.gif
   :align: center

|

**SNUB is a visual interface** for systems neuroscience. Using a set of linked data-views, users can explore relationships between raw video, 3D animal pose, behavior annotations, neural activity, or any other relevant time-series data.

Loading data is simple with the ``snub.io`` module. For example the following code creates a new project with paired electrophysiology and video data. 

.. code-block:: python

   import snub.io

   project_directory = 'path/to/new/project'

   snub.io.create_project(project_directory, duration=1800)
   snub.io.add_video(project_directory, 'path/to/my_video.avi', name='IR_camera')
   snub.io.add_splikeplot(project_directory, 'my_ephys_data', spike_times, spike_labels) 


SNUB Documentation
------------------

.. toctree::
   :maxdepth: 2

   install

   tutorials

   nwb

   snub.io<api>



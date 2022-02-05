Systems Neuro Browser
================================



**SNUB is a visual interface for time-series data in systems neuroscience.** Using a set of linked views, users can explore relationships between raw video, animal pose, behavior annotations, and neural activity. Some example use cases are shown below below, followed by detailed 

Use Cases
---------

1. Caption blah
.. image:: ../media/screen_capture1.gif

2. Caption blah
.. image:: ../media/screen_capture3.gif

3. Caption blah
.. image:: ../media/screen_capture4.gif

Installation
------------

Install `Anaconda <https://docs.anaconda.com/anaconda/install/index.html>`_ or `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_. Create an environment with python≥3.7 and pip install SNUB. 

.. code-block:: console

   conda create -n snub python=3.7
   conda activate snub
   pip install -U git+https://github.com/calebweinreb/SNUB

To test the installation, download the example data and start SNUB by running::

   snub

(make sure the conda environment is activated). A browser window should launch. Go to ``File > Open Project``,  navigate to one of the example projects, and hit ``Choose`` with the project directory selected. Alternatively, you can launch snub with the project path as a command line argument::

   snub /path/to/project/directory

.. note:: 

   If you have macOS Big Sur, opengl-based features such as the 3D mesh view `will only work <https://github.com/PixarAnimationStudios/USD/issues/1372#issuecomment-716925973>`_ if edit::

      ~/miniconda3/envs/snub/lib/python3.7/site-packages/OpenGL/platform/ctypesloader.py

   by replacing the following line::

      # fullName = util.find_library( name ) # <- comment this line out
      fullName = '/System/Library/Frameworks/OpenGL.framework/OpenGL' # <- use this line instead



Loading Data
------------

The ``snub.io`` module provides a set of functions for creating a new project and saving common types of data. For example, the following code creates a new project with paired electrophysiology and video data. For other data types and additional options, see the snub.io documentation. 

.. code-block:: python

   import snub.io

   project_directory = 'path/to/new/project'

   snub.io.create_project(project_directory, duration=1800)
   snub.io.add_video(project_directory, 'path/to/my_video.avi', name='IR_camera')
   snub.io.add_ephys(ephys_data) # ephys_data is a list of spike times for each unit


Another option is to create a SNUB project manually. Each project is simply a directory with data and a ``config.json`` file. The config file contains a set of global parameters and list of desired data-views, such as videos, raster plots, or scatter splots. See below for a full list of available data-views. 

.. toctree::
   :maxdepth: 2

   setup


Browser Guide
-------------



.. toctree::
   :maxdepth: 2

   usage


Developer API
-------------

.. toctree::
   :maxdepth: 2

   api



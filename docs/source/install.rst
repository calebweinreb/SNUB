Installation
============

Install Conda
----------------

Install `Anaconda <https://docs.anaconda.com/anaconda/install/index.html>`_ or `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_. Create an environment called ``snub`` with python≥3.8::

   conda create -n snub python=3.8


Activate the environment::

   conda activate snub


Install SNUB
------------

Install SNUB using ``pip``::

   pip install snub

To speed up selections, we recommend installing ``ncls``::

   pip install ncls

To use the 3D mesh viewer, install ``opengl``::

   pip install PyOpenGL PyOpenGL_accelerate

Test SNUB
---------

To test the installation, try launching ``snub`` from the command line (make sure the ``snub`` conda environment is activated)::

   snub

A browser window should launch. Download the `example project <https://www.dropbox.com/sh/tz6kokymkpjicfb/AABBpFzqwFEdFfuXPzhv3Q_6a?dl=0>`_, and try opening it by going to ``File > Open Project``, navigating to the project directory, and hitting ``Choose`` with the directory selected. Projects can also be opened by including the path as a command line argument::

   snub /path/to/project/directory


SNUB + Jupyter
--------------

To use SNUB functions in a jupyter notebook, execute the following line with the ``snub`` environment active. The environment should then be listed as an option when creating a new notebook or when switching kernels (``Kernel > Change Kernel > snub``)::

   python -m ipykernel install --user --name=snub

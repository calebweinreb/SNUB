import setuptools

with open("README.md", 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='snub',
    version='0.0.0',
    author='Caleb Weinreb',
    author_email='calebsw@gmail.com',
    description='Systems neuro browser',
    long_description=long_description,
    long_description_content_type='text/markdown',
    include_package_data=True,
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent'
    ],
    entry_points={
        'console_scripts':[
            'snub = snub.gui.main:run']
    },
    python_requires='>=3.8',
    install_requires=['PyQt5',
                      'numpy',
                      'scikit-learn',
                      'pynndescent',
                      'tqdm',
                      'cmapy',
                      'ncls',
                      'interlap',
                      'numba',
                      'vispy',
                      'imageio',
                      'imageio-ffmpeg',
                      'umap-learn',
                      'rastermap',
                      'ipykernel',
                      'pyqtgraph',
                      'PyOpenGL',
                      'PyOpenGL_accelerate',
                      'opencv-python-headless',
                      'vidio>=0.0.3'], 
    url='https://github.com/jbohnslav/pose_annotator'
)

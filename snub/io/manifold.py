import numpy as np

import warnings

def sort(
    data, 
    method='rastermap', 
    options={}
):
    """Linearly sort neurons in order to group those with similar activity

    Parameters
    ----------
    method: {'rastermap'}
        Method to use for sorting (currently only rastermap is implemented)

    options: dict, default={}
        Sorting method-specific options.

        'rastermap'
            ``options`` will be passed as keyword arguments when initializing
            `rastermap.mapping.Rastermap <https://github.com/MouseLand/rastermap/blob/40867ce9a8b2850d76483890740c0dc10d6cb413/rastermap/mapping.py#L531>`_
    """
    valid_sort_methods = ['rastermap']
    if not method in valid_sort_methods:
        raise AssertionError(method+' is not a valid sort method. Must be one of '+repr(valid_sort_methods))
    if method=='rastermap':
        print('Computing row order with rastermap')
        from rastermap import mapping
        model = mapping.Rastermap(n_components=1).fit(data)
        return np.argsort(model.embedding[:,0])

    
def firing_rates(
    spike_times, 
    spike_labels, 
    window_size=0.2, 
    window_step=0.02
):
    """Convert spike tikes to firing rates using a sliding window
    
    Parameters
    ----------
    spike_times : ndarray
        Spike times (in seconds) for all units. The source of each spike is
        input separately using ``spike_labels``
        
    spike_labels: ndarray
        The source/label for each spike in ``spike_times``. The maximum
        value of this array determines the number of rows in the heatmap.
    
    window_size: float, default=0.2
        Length (in seconds) of the sliding window used to calculate firing rates
        
    window_step: float, default=0.02
        Step-size (in seconds) between each window used to calculate firing rates

    Returns
    -------
    firing_rates: ndarray
        Array of firing rates, where rows units and columns are sliding 
        window locations. ``firing_rates`` has shape ``(N,M)`` where::

            N = max(spike_labels)+1

            M = (max(spike_times)-min(spike_times))/binsize

    start_time, float
        The time (in seconds) corresponding to the left-boundary
        of the first window in ``firing_rates``.
    """
    # round spikes to window_step and factor our start time
    spike_times = np.around(spike_times/window_step).astype(int)
    start_time = spike_times.min()
    spike_times = spike_times - start_time
    
    # create heatmap of spike counts for each window_step-sized bin
    spike_labels = spike_labels.astype(int)
    heatmap = np.zeros((spike_labels.max()+1, spike_times.max()+1))
    np.add.at(heatmap, (spike_labels, spike_times), 1/window_step)
    
    # use convolution to get sliding window counts
    kernel = np.ones(int(window_size//window_step))/(window_size//window_step)
    for i in range(heatmap.shape[0]): heatmap[i,:] = np.convolve(heatmap[i,:],kernel, mode='same')
    return heatmap, start_time-window_step/2


def bin_data(
    data, 
    binsize
):
    """Bin data column-wise using non-overlaping windows.

    Parameters
    ----------
    data: ndarray
        Data for binning, where rows are variables and columns are observations.

    binsize: int
        Width of the window used for binning

    Returns
    -------
    data_binned: ndarray

    bin_intervals: ndarray
        (N,2) array with the start and end index of each bin
    """
    pad_amount = (-data.shape[1])%binsize
    num_bins = int((data.shape[1]+pad_amount)/binsize)

    data_padded = np.pad(data,((0,0),(0,pad_amount)))
    data_binned = data_padded.reshape(-1, num_bins, binsize).mean(2)
    if pad_amount > 0: data_binned[:,-1] = data_binned[:,-1] * binsize/pad_amount

    bin_starts = np.arange(0,num_bins)*binsize
    bin_ends = np.arange(1,num_bins+1)*binsize
    bin_ends[-1] = data.shape[1]
    bin_intervals = np.vstack((bin_starts,bin_ends)).T

    return data_binned, bin_intervals

def zscore(data, axis=0, eps=1e-10):
    mean = np.mean(data, axis=axis, keepdims=True)
    std = np.std(data, axis=axis, keepdims=True) + eps
    return (data-mean)/std

def umap_embedding(
    data, 
    standardize=True,
    n_pcs=20, 
    n_components=2, 
    n_neighbors=100,
    **kwargs
):
    """Generate a 2D embedding of neural activity using UMAP. The function 
    generates the embedding in three steps:

        1. (Optionally) standardize (Z-score) the activity of each neuron

        2. Perform initial dimensionality reduction using PCA

        3. Run UMAP on the output of PCA

    Parameters
    ----------
    data: ndarray
        Array of neural activity where rows are neurons and columns are time points

    standardize: bool, default=True
        Whether to standardize (Z-score) the data prior to PCA

    n_pcs: int, default=20
        Number of principal components to use during PCA. If ``n_pcs=None``, the binned 
        data will be passed directly to UMAP

    n_components: int, default=2
        Dimensionality of the embedding

    n_neighbors: int, default=100
        Passed to UMAP (see `explanation of UMAP parameters <https://umap-learn.readthedocs.io/en/latest/parameters.html>`_).

    **kwargs
        Any other UMAP parameters can also be passed as keyword arguments

    Returns
    -------
    coodinates: ndarray
        (N,2) array containing UMAP coordinates
    """
    from sklearn.decomposition import PCA
    from umap import UMAP

    if standardize: data = zscore(data, axis=1)
    PCs = PCA(n_components=n_pcs).fit_transform(data.T)
    umap_obj = UMAP(n_neighbors=n_neighbors, n_components=n_components, n_epochs=500, **kwargs)
    coordinates = umap_obj.fit_transform(PCs)
    return coordinates







    
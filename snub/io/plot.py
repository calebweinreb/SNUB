import numpy as np


def scatter_plot_bounds(xy, margin=0.05, n_neighbors=100, distance_cutoff=2):
    """
    Get xlim and ylim for a scatter plot such that outliers are excluded.
    Bounds are based on the largest component of a knn graph with distance cutoff.
    """
    import pynndescent, networkx as nx

    edges, dists = pynndescent.NNDescent(xy, n_neighbors=n_neighbors).neighbor_graph
    G = nx.Graph()
    G.add_nodes_from(np.arange(xy.shape[0]))
    for i, j in zip(*np.nonzero(dists < distance_cutoff)):
        G.add_edge(i, edges[i, j])
    comps = list(nx.connected_components(G))
    largest_comp = np.array(list(comps[np.argmax([len(c) for c in comps])]))
    xlim = [xy[largest_comp, 0].min(), xy[largest_comp, 0].max()]
    ylim = [xy[largest_comp, 1].min(), xy[largest_comp, 1].max()]
    xlim = [
        xlim[0] - margin * (xlim[1] - xlim[0]),
        xlim[1] + margin * (xlim[1] - xlim[0]),
    ]
    ylim = [
        ylim[0] - margin * (ylim[1] - ylim[0]),
        ylim[1] + margin * (ylim[1] - ylim[0]),
    ]
    return xlim, ylim

import numpy as np
from numba import njit, prange



#@njit 
def sum_by_index(x, ixs, n):
    out = np.zeros(n)
    for i in prange(len(ixs)):
        out[ixs[i]] += x[i]
    return out


class IntervalIndexBase():
    def __init__(self, intervals=np.empty((0,2)), **kwargs):
        self.intervals = intervals

    def partition_intervals(self, start, end):
        ends_before = self.intervals[:,1] < start
        ends_after = self.intervals[:,1] >= start
        starts_before = self.intervals[:,0] <= end
        starts_after = self.intervals[:,0] > end
        intersect = self.intervals[np.bitwise_and(ends_after, starts_before)]
        pre = self.intervals[ends_before]
        post = self.intervals[starts_after]
        return pre,intersect,post
        
    def add_interval(self, start, end):
        pre,intersect,post = self.partition_intervals(start,end)
        if intersect.shape[0] > 0:
            merged_start = np.minimum(intersect[0,0],start)
            merged_end = np.maximum(intersect[-1,1],end)
        else: 
            merged_start, merged_end = start, end
        merged_interval = np.array([merged_start, merged_end]).reshape(1,2)
        self.intervals = np.vstack((pre, merged_interval, post))

    def remove_interval(self, start, end):
        pre,intersect,post = self.partition_intervals(start,end)
        pre_intersect = np.empty((0,2))
        post_intersect = np.empty((0,2))
        if intersect.shape[0] > 0:
            if intersect[0,0] < start: pre_intersect = np.array([intersect[0,0],start])
            if intersect[-1,1] > end: post_intersect = np.array([end,intersect[-1,1]])
        self.intervals = np.vstack((pre,pre_intersect,post_intersect,post))

    def intersection_proportions(self, query_intervals): 
        query_ixs, ref_ixs = self.all_overlaps_both(self.intervals, query_intervals)
        if len(query_ixs)>0:
            intersection_starts = np.maximum(query_intervals[query_ixs,0], self.intervals[ref_ixs,0])
            intersection_ends = np.minimum(query_intervals[query_ixs,1], self.intervals[ref_ixs,1])
            intersection_lengths = intersection_ends - intersection_starts
            query_intersection_lengths = sum_by_index(intersection_lengths, query_ixs, query_intervals.shape[0])
            query_lengths = query_intervals[:,1] - query_intervals[:,0] + 1e-10
            return query_intersection_lengths / query_lengths
        else: return np.zeros(query_intervals.shape[0])

    def intervals_containing(self, query_locations):
        return self.all_containments_both(self.intervals, query_locations)[1]


try:

    from ncls import NCLS
    class IntervalIndex(IntervalIndexBase):
        def __init__(self, min_step=0.033, **kwargs):
            super().__init__(**kwargs)
            self.min_step = min_step

        def preprocess_for_ncls(self, intervals):
            intervals_discretized = (intervals/self.min_step).astype(int)
            return (intervals_discretized[:,0].copy(order='C'),
                    intervals_discretized[:,1].copy(order='C'),
                    np.arange(intervals_discretized.shape[0]))

        def all_containments_both(self, ref_intervals, query_locations):
            query_locations = (query_locations / self.min_step).astype(int)
            ncls = NCLS(*self.preprocess_for_ncls(self.intervals))
            return ncls.all_containments_both(query_locations,query_locations, np.arange(len(query_locations)))

        def all_overlaps_both(self, ref_intervals, query_intervals):
            query_intervals = self.preprocess_for_ncls(query_intervals)
            ref_intervals = self.preprocess_for_ncls(ref_intervals)
            ncls = NCLS(*ref_intervals)
            return ncls.all_overlaps_both(*query_intervals)

except:

    from interlap import InterLap
    class IntervalIndex(IntervalIndexBase):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def all_overlaps_both(self, ref_intervals, query_intervals):
            inter = InterLap(ranges=[(s,e,i) for i,(s,e) in enumerate(ref_intervals)])
            query_ixs,ref_ixs = [],[]
            for i,(s,e) in enumerate(query_intervals):
                overlap_ixs = [interval[2] for interval in inter.find((s,e))]
                ref_ixs.append(overlap_ixs)
                query_ixs.append([i]*len(overlap_ixs))
            return np.hstack(query_ixs).astype(int),np.hstack(ref_ixs).astype(int)

        def all_containments_both(self, ref_intervals, query_locations):
            query_intervals = np.repeat(query_locations[:,None],2,axis=1)
            return self.all_overlaps_both(ref_intervals, query_intervals)






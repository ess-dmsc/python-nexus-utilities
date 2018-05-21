import numpy as np
import h5py
from .nxloghelper import create_nexus_file
try:
    import matplotlib.pyplot as pl
except:
    pass

"""
This script shows how one can use the new "cue" features of NXlog and NXevent_data to extract a subset of the data
"""

if __name__ == '__main__':
    # Make an example file with a fabricated NXlog and some real neutron event data in it
    filename = 'SANS2D_NXlog_example.hdf5'
    create_nexus_file(filename)

    # Open the NeXus file
    with h5py.File(filename, 'r') as nexus_file:
        # Inexplicably, my fictitious experiment involved a plant sample which rapidly grew during data collection
        # The plant's height was measured by an auxanometer and values are recorded in an NXlog in the file
        plant_log = nexus_file.get('raw_data_1/sample/auxanometer_1')

        # Something particularly interesting happened between 832 and 846 seconds after the start of the experiment.
        # We therefore want to extract the plant height data for this period.
        # We could just read in all the timestamp data and then truncate them to the range of interest,
        # but there may be more data than fit in memory, or at least enough that finding where to truncate them is slow.
        # Alternatively, we could read individual timestamps and do a binary search for the start and end of
        # the time period, but that is more complicated to implement than a linear search and could also
        # be inefficient if the sample rate varied over the experiment.
        # Instead we can use "cues" which were recorded periodically when the file was written.
        # It is up to the file writer when cues are recorded, for example they could be at regular time intervals,
        # correspond to neutron pulses, be recorded for the start of each message if the data arrives from a
        # network stream, or be recorded for the start of each HDF5 compressed chunk to optimise read performance.

        # cue_timestamp_zero is a small subset of timestamps from the full timestamps dataset
        # Since it is small we can load the whole dataset from file with [...]
        cue_timestamps = plant_log['cue_timestamp_zero'][...]
        # cue_index maps between indices in the cue timestamps and the full timestamps dataset
        cue_indices = plant_log['cue_index'][...]

        # We look up the positions in the full timestamp list where the cue timestamps are in our range of interest
        range_start, range_end = 832, 846
        range_indices = cue_indices[np.append((range_start < cue_timestamps[1:]), [True]) &
                                    np.append([True], (range_end > cue_timestamps[:-1]))][[0, -1]]

        # Now we can extract a slice of the log which we know contains the time range we are interested in
        times = plant_log['time'][range_indices[0]:range_indices[1]]
        values = plant_log['value'][range_indices[0]:range_indices[1]]

        # We can easily truncate them to the exact range if necessary
        times_mask = (range_start <= times) & (times <= range_end)
        times = times[times_mask]
        values = values[times_mask]
        try:
            pl.plot(times, values)
            pl.show()
        except:
            pass

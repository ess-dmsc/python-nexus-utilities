import h5py
import random
import numpy as np
from nexusutils.utils import create_dataset


def generate_fake_events(nexus_entry: h5py._hl.group.Group, events_per_pulse, number_of_pulses, pulse_freq_hz=10.0,
                         tof_min_ns=0,
                         tof_max_ns=50000000):
    """
    Adds fake event data to every NXdetector group
    TOF and detector ID for each event is random

    Returns an array of all detector IDs in the instrument - this can be used to create a detector-spectrum map
    """
    all_ids = np.array([], dtype=np.uint32)
    event_time_zero = __generate_pulse_times(number_of_pulses, pulse_freq_hz)
    event_index = __generate_event_index(number_of_pulses, events_per_pulse)
    for instrument in __get_nodes_of_class(nexus_entry, 'NXinstrument'):
        for detector in __get_nodes_of_class(instrument, 'NXdetector'):
            det_ids = __get_detector_id_list(detector)
            all_ids = np.append(all_ids, det_ids)
            event_id = np.array([], dtype=np.uint32)
            event_time_offset = np.array([], dtype=np.uint64)
            for _ in range(number_of_pulses):
                for _ in range(events_per_pulse):
                    event_id = np.append(event_id, det_ids[random.randint(0, len(det_ids) - 1)])
                    event_time_offset = np.append(event_time_offset, random.randint(tof_min_ns, tof_max_ns))
            event_group = detector.create_group('event_data')
            event_group.attrs.create('NX_class', np.array('NXevent_data').astype('|S12'))
            create_dataset(nexus_entry, event_group, 'event_time_zero', event_time_zero, {'units': 'ns'})
            create_dataset(nexus_entry, event_group, 'event_index', event_index)
            create_dataset(nexus_entry, event_group, 'event_id', event_id)
            create_dataset(nexus_entry, event_group, 'event_time_offset', event_time_offset, {'units': 'ns'})

            # Also create a link to the event data in the entry group
            nexus_entry['event_data_{}'.format(detector.name.split('/')[-1])] = event_group
    return all_ids


def __get_nodes_of_class(parent_group, class_name):
    for node in parent_group:
        nexus_class = parent_group[node].attrs.get('NX_class')
        if nexus_class:
            if nexus_class.decode("utf-8") == class_name:
                yield parent_group[node]


def __get_detector_id_list(detector):
    return detector['detector_number'][...].flatten()


def __generate_pulse_times(number_of_pulses, pulse_freq_hz):
    pulse_period_ns = int((1.0 / pulse_freq_hz) * 1e9)
    return np.arange(0, number_of_pulses * pulse_period_ns, pulse_period_ns, np.uint64)


def __generate_event_index(number_of_pulses, events_per_pulse):
    return np.arange(0, number_of_pulses * events_per_pulse, events_per_pulse)

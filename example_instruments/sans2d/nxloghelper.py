from collections import OrderedDict
from nexusbuilder import NexusBuilder
import numpy as np
from datetime import datetime


def create_nexus_file(output_filename):
    # compress_type=32001 for BLOSC, or don't specify compress_type and opts to get non-compressed datasets
    builder = NexusBuilder(output_filename, input_nexus_filename='SANS_test.nxs',
                           idf_file='SANS2D_Definition_Tubes.xml', compress_type='gzip', compress_opts=1)

    builder.add_instrument_geometry_from_idf()
    add_example_nxlog(builder)
    __copy_data_from_existing_file(builder)


def __copy_data_from_existing_file(builder):
    builder.add_user('Sans2d Team', 'ISIS, STFC')
    builder.copy_items(OrderedDict([('raw_data_1/instrument/moderator', 'raw_data_1/instrument/moderator'),
                                    ('raw_data_1/instrument/moderator/distance',
                                     'raw_data_1/instrument/moderator/distance'),
                                    ('raw_data_1/instrument/source/probe', 'raw_data_1/instrument/source/probe'),
                                    ('raw_data_1/instrument/source/type', 'raw_data_1/instrument/source/type'),
                                    ('raw_data_1/sample/name', 'raw_data_1/sample/name'),
                                    ('raw_data_1/sample/type', 'raw_data_1/sample/type'),
                                    ('raw_data_1/good_frames', 'raw_data_1/good_frames'),
                                    ('raw_data_1/duration', 'raw_data_1/duration'),
                                    ('raw_data_1/start_time', 'raw_data_1/start_time'),
                                    ('raw_data_1/end_time', 'raw_data_1/end_time'),
                                    ('raw_data_1/run_cycle', 'raw_data_1/run_cycle'),
                                    ('raw_data_1/title', 'raw_data_1/title'),
                                    ('raw_data_1/detector_1_events',
                                     'raw_data_1/detector_1_events'),
                                    ('raw_data_1/detector_1_events/event_id',
                                     'raw_data_1/detector_1_events/event_id'),
                                    ('raw_data_1/detector_1_events/total_counts',
                                     'raw_data_1/detector_1_events/total_counts'),
                                    ('raw_data_1/detector_1_events/event_index',
                                     'raw_data_1/detector_1_events/event_index'),
                                    ('raw_data_1/detector_1_events/event_time_zero',
                                     'raw_data_1/detector_1_events/event_time_zero'),
                                    ('raw_data_1/detector_1_events/event_time_offset',
                                     'raw_data_1/detector_1_events/event_time_offset'),
                                    ('raw_data_1/monitor_1/data', 'raw_data_1/instrument/monitor1/data'),
                                    ('raw_data_1/monitor_1/time_of_flight',
                                     'raw_data_1/instrument/monitor1/time_of_flight'),
                                    ('raw_data_1/monitor_2/data', 'raw_data_1/instrument/monitor2/data'),
                                    ('raw_data_1/monitor_2/time_of_flight',
                                     'raw_data_1/instrument/monitor2/time_of_flight'),
                                    ('raw_data_1/monitor_3/data', 'raw_data_1/instrument/monitor3/data'),
                                    ('raw_data_1/monitor_3/time_of_flight',
                                     'raw_data_1/instrument/monitor3/time_of_flight'),
                                    ('raw_data_1/monitor_4/data', 'raw_data_1/instrument/monitor4/data'),
                                    ('raw_data_1/monitor_4/time_of_flight',
                                     'raw_data_1/instrument/monitor4/time_of_flight'),
                                    ]))


def add_example_nxlog(builder, parent_path='/raw_data_1/sample/', number_of_cues=1000):
    """
    Adds example NXlog class to the file
    """
    time = 0.0
    index = 0
    cue_timestamps = []
    cue_indices = []
    times = np.array([])
    values = np.array([])
    for cue_number in range(number_of_cues):
        number_of_samples = np.random.randint(number_of_cues * 10, number_of_cues * 20)
        cue_timestamps.append(time)
        cue_indices.append(index)
        time += 0.2 * number_of_cues + (np.random.rand() * 20)
        if cue_number > 0:
            values = np.hstack([values, np.sort(np.random.rand(number_of_samples) * (1/number_of_cues)) + values[-1]])
            times = np.hstack(
                (
                    times,
                    cue_timestamps[-1] + (np.sort(np.random.rand(number_of_samples)) * (time - cue_timestamps[-1]))))
        else:
            values = np.sort(np.random.rand(number_of_samples) * (1/number_of_cues)) + 0.21
            times = np.sort(np.random.rand(number_of_samples)) * time
        index += number_of_samples

    # Create an NXlog group in the sample group
    iso_timestamp = datetime.now().isoformat()
    data_group = builder.add_nx_group(parent_path, 'auxanometer_1', 'NXlog')
    builder.add_dataset(data_group, 'time', times.astype('float32'), {'units': 's', 'start': iso_timestamp})
    builder.add_dataset(data_group, 'value', values.astype('float32'), {'units': 'cubits'})
    builder.add_dataset(data_group, 'cue_timestamp_zero', np.array(cue_timestamps).astype('float32'),
                        {'units': 's', 'start': iso_timestamp})
    builder.add_dataset(data_group, 'cue_index', np.array(cue_indices).astype('int32'))

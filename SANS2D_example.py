from copy_items import *

if __name__ == '__main__':
    out_file = 'SANS_example_noComp.hdf5'
    wipe_file(out_file)

    d = OrderedDict([('b', 2), ('a', 1)])
    copy_l_to_r = \
        OrderedDict([('raw_data_1', 'raw_data_1'),
                     ('/raw_data_1/detector_1_events', '/raw_data_1/detector_1_events'),
                     ('/raw_data_1/detector_1_events/event_id', '/raw_data_1/detector_1_events/event_id'),
                     ('/raw_data_1/detector_1_events/total_counts', '/raw_data_1/detector_1_events/total_counts'),
                     ('/raw_data_1/detector_1_events/event_index', '/raw_data_1/detector_1_events/event_index'),
                     ('/raw_data_1/detector_1_events/event_time_zero', '/raw_data_1/detector_1_events/event_time_zero'),
                     ('/raw_data_1/good_frames', '/raw_data_1/good_frames'),
                     ('/raw_data_1/detector_1_events/event_time_offset',
                      '/raw_data_1/detector_1_events/event_time_offset')
                     ])

    copy_items('SANS_test.nxs', out_file, copy_l_to_r, compress_type=None)
    # copy_items('SANS_test.nxs', 'SANS_example_gzip.hdf5', copy_l_to_r, compress_type='gzip', compress_opts=1)
    # copy_items('SANS_test.nxs', 'SANS_example_blosc.hdf5', copy_l_to_r, compress_type=32001)
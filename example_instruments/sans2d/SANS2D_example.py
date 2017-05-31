from collections import OrderedDict
from nexusbuilder import NexusBuilder

if __name__ == '__main__':
    copy_l_to_r = \
        OrderedDict([('raw_data_1/good_frames', 'raw_data_1/good_frames'),
                     ('raw_data_1/duration', 'raw_data_1/duration'),
                     ('raw_data_1/start_time', 'raw_data_1/start_time'),
                     ('raw_data_1/end_time', 'raw_data_1/end_time'),
                     ('raw_data_1/run_cycle', 'raw_data_1/run_cycle'),
                     ('raw_data_1/title', 'raw_data_1/title'),
                     ('raw_data_1/definition', 'raw_data_1/definition'),
                     ('raw_data_1/instrument', 'raw_data_1/instrument'),
                     ('raw_data_1/instrument/name', 'raw_data_1/instrument/name'),
                     ('raw_data_1/instrument/source', 'raw_data_1/instrument/source'),
                     ('raw_data_1/instrument/source/name', 'raw_data_1/instrument/source/name'),
                     ('raw_data_1/instrument/source/probe', 'raw_data_1/instrument/source/probe'),
                     ('raw_data_1/instrument/source/type', 'raw_data_1/instrument/source/type'),
                     ('raw_data_1/instrument/moderator', 'raw_data_1/instrument/moderator'),
                     ('raw_data_1/instrument/moderator/distance', 'raw_data_1/instrument/moderator/distance'),
                     ])

    builder = NexusBuilder('SANS_test.nxs', 'SANS_example_noComp.hdf5', idf_filename='SANS2D_Definition_Tubes.xml')
    # builder = NexusBuilder('SANS_test.nxs', 'SANS_example_gzip.hdf5', idf_filename='SANS2D_Definition.xml',
    #                        compress_type='gzip', compress_opts=1)
    # builder = NexusBuilder('SANS_test.nxs', 'SANS_example_blosc.hdf5', idf_filename='SANS2D_Definition.xml',
    #                        compress_type=32001)
    builder.copy_items(copy_l_to_r)
    builder.add_user('Sans2d Team', 'ISIS, STFC')

    # Add the first detector panel
    detector_group_1 = builder.add_detector('rear-detector', 1)
    builder.copy_items(OrderedDict([('raw_data_1/detector_1_events',
                                     'raw_data_1/instrument/detector_1/events'),
                                    ('raw_data_1/detector_1_events/event_id',
                                     'raw_data_1/instrument/detector_1/events/event_id'),
                                    ('raw_data_1/detector_1_events/total_counts',
                                     'raw_data_1/instrument/detector_1/events/total_counts'),
                                    ('raw_data_1/detector_1_events/event_index',
                                     'raw_data_1/instrument/detector_1/events/event_index'),
                                    ('raw_data_1/detector_1_events/event_time_zero',
                                     'raw_data_1/instrument/detector_1/events/event_time_zero'),
                                    ('raw_data_1/detector_1_events/event_time_offset',
                                     'raw_data_1/instrument/detector_1/events/event_time_offset'),
                                    ]))
    left_tubes = builder.add_grid_pattern(detector_group_1, 'left_tubes', 1100000, [-0.5192, -0.48195, 0], [512, 60],
                                          [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    builder.add_tube_pixel(left_tubes, 0.002033984375, 0.00405)
    # TODO add NXtransformation for z displacement of 23.281 from source
    right_tubes = builder.add_grid_pattern(detector_group_1, 'right_tubes', 1101000, [-0.5222, -0.473855, 0],
                                           [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    # TODO add a link to the pixel in left_tubes instead of repeating the definition
    builder.add_tube_pixel(right_tubes, 0.002033984375, 0.00405)

    # Add the second detector panel
    detector_group_2 = builder.add_detector('front-detector', 2)
    # TODO add NXtransformation for z displacement of 23.281 from source and displacement on y axis
    left_tubes_2 = builder.add_grid_pattern(detector_group_2, 'left_tubes', 1100000, [-0.5192, -0.48195, 0], [512, 60],
                                            [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    builder.add_tube_pixel(left_tubes_2, 0.002033984375, 0.00405)
    right_tubes_2 = builder.add_grid_pattern(detector_group_2, 'right_tubes', 1101000, [-0.5222, -0.473855, 0],
                                             [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    builder.add_tube_pixel(right_tubes_2, 0.002033984375, 0.00405)

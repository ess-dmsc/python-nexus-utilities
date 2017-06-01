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
                     ('raw_data_1/sample', 'raw_data_1/instrument/sample'),
                     ('raw_data_1/sample/distance', 'raw_data_1/instrument/sample/distance'),
                     ('raw_data_1/sample/name', 'raw_data_1/instrument/sample/name'),
                     ('raw_data_1/sample/type', 'raw_data_1/instrument/sample/type'),
                     ('raw_data_1/monitor_1', 'raw_data_1/instrument/monitor_1'),
                     ('raw_data_1/monitor_1/data', 'raw_data_1/instrument/monitor_1/data'),
                     ('raw_data_1/monitor_1/time_of_flight', 'raw_data_1/instrument/monitor_1/time_of_flight'),
                     ('raw_data_1/monitor_2', 'raw_data_1/instrument/monitor_2'),
                     ('raw_data_1/monitor_2/data', 'raw_data_1/instrument/monitor_2/data'),
                     ('raw_data_1/monitor_2/time_of_flight', 'raw_data_1/instrument/monitor_2/time_of_flight'),
                     ('raw_data_1/monitor_3', 'raw_data_1/instrument/monitor_3'),
                     ('raw_data_1/monitor_3/data', 'raw_data_1/instrument/monitor_3/data'),
                     ('raw_data_1/monitor_3/time_of_flight', 'raw_data_1/instrument/monitor_3/time_of_flight'),
                     ('raw_data_1/monitor_4', 'raw_data_1/instrument/monitor_4'),
                     ('raw_data_1/monitor_4/data', 'raw_data_1/instrument/monitor_4/data'),
                     ('raw_data_1/monitor_4/time_of_flight', 'raw_data_1/instrument/monitor_4/time_of_flight'),
                     ('raw_data_1/monitor_5', 'raw_data_1/instrument/monitor_5'),
                     ('raw_data_1/monitor_5/data', 'raw_data_1/instrument/monitor_5/data'),
                     ('raw_data_1/monitor_5/time_of_flight', 'raw_data_1/instrument/monitor_5/time_of_flight'),
                     ('raw_data_1/monitor_6', 'raw_data_1/instrument/monitor_6'),
                     ('raw_data_1/monitor_6/data', 'raw_data_1/instrument/monitor_6/data'),
                     ('raw_data_1/monitor_6/time_of_flight', 'raw_data_1/instrument/monitor_6/time_of_flight'),
                     ('raw_data_1/monitor_7', 'raw_data_1/instrument/monitor_7'),
                     ('raw_data_1/monitor_7/data', 'raw_data_1/instrument/monitor_7/data'),
                     ('raw_data_1/monitor_7/time_of_flight', 'raw_data_1/instrument/monitor_7/time_of_flight'),
                     ('raw_data_1/monitor_8', 'raw_data_1/instrument/monitor_8'),
                     ('raw_data_1/monitor_8/data', 'raw_data_1/instrument/monitor_8/data'),
                     ('raw_data_1/monitor_8/time_of_flight', 'raw_data_1/instrument/monitor_8/time_of_flight'),
                     ])

    builder = NexusBuilder('SANS_test.nxs', 'SANS_example_noComp.hdf5', idf_filename='SANS2D_Definition_Tubes.xml')
    # builder = NexusBuilder('SANS_test.nxs', 'SANS_example_gzip.hdf5', idf_filename='SANS2D_Definition.xml',
    #                        compress_type='gzip', compress_opts=1)
    # builder = NexusBuilder('SANS_test.nxs', 'SANS_example_blosc.hdf5', idf_filename='SANS2D_Definition.xml',
    #                        compress_type=32001)
    builder.copy_items(copy_l_to_r)
    builder.add_user('Sans2d Team', 'ISIS, STFC')

    # Add the first detector panel
    # This panel is centred on the beam centre
    # 23.281 is the displacement along the beam (z-axis) from source, not sample. Should this be changed... (L2 ~4m)
    detector_group_1 = builder.add_detector('rear-detector', 1)
    # Copy event data from the existing NeXus file
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
    left_tubes = builder.add_grid_pattern(detector_group_1, 'left_tubes', 1100000, [-0.5192, -0.48195, 23.281],
                                          [512, 60],
                                          [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    builder.add_tube_pixel(left_tubes, 0.002033984375, 0.00405)
    right_tubes = builder.add_grid_pattern(detector_group_1, 'right_tubes', 1101000, [-0.5222, -0.473855, 23.281],
                                           [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    builder.add_tube_pixel(right_tubes, 0.002033984375, 0.00405)

    # Add the second detector panel
    # This panel is displaced by -1.1m on the x axis from the beam centre
    detector_group_2 = builder.add_detector('front-detector', 2)
    left_tubes_2 = builder.add_grid_pattern(detector_group_2, 'left_tubes', 1100000, [-0.5192-1.1, -0.48195, 23.281],
                                            [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    builder.add_tube_pixel(left_tubes_2, 0.002033984375, 0.00405)
    right_tubes_2 = builder.add_grid_pattern(detector_group_2, 'right_tubes', 1101000, [-0.5222-1.1, -0.473855, 23.281],
                                             [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]))
    builder.add_tube_pixel(right_tubes_2, 0.002033984375, 0.00405)

from collections import OrderedDict
from nexusbuilder import NexusBuilder

if __name__ == '__main__':
    # builder = NexusBuilder('SANS_example_no_compression.hdf5', 'SANS_test.nxs',
    #                        idf_filename='SANS2D_Definition_Tubes.xml')
    builder = NexusBuilder('SANS_example_gzip_compress.hdf5', 'SANS_test.nxs',
                           idf_file='SANS2D_Definition_Tubes.xml', compress_type='gzip', compress_opts=1)
    # builder = NexusBuilder('SANS_example_blosc_compress.hdf5', 'SANS_test.nxs',
    #                        idf_filename='SANS2D_Definition_Tubes.xml', compress_type=32001)

    # Adds all instrument geometry except non-monitor detectors
    sample_position = builder.add_instrument_geometry_from_idf()

    # Add the first detector panel
    # This panel is centred on the beam centre
    # 4.0 is the displacement along the beam (z-axis) from the sample (L2 distance)
    detector_group_1 = builder.add_detector_minimal('rear-detector', 1)
    left_tubes = builder.add_grid_pattern(detector_group_1, 'left_tubes', 1100000, [-0.5192, -0.48195, 4.0],
                                          [512, 60],
                                          [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]),
                                          depends_on=sample_position)
    builder.add_tube_pixel(left_tubes, 0.002033984375, 0.00405)
    right_tubes = builder.add_grid_pattern(detector_group_1, 'right_tubes', 1101000, [-0.5222, -0.473855, 4.0],
                                           [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]),
                                           depends_on=sample_position)
    builder.add_tube_pixel(right_tubes, 0.002033984375, 0.00405)

    # Add the second detector panel
    # This panel is displaced by -1.1m on the x axis from the beam centre
    detector_group_2 = builder.add_detector_minimal('front-detector', 2)
    left_tubes_2 = builder.add_grid_pattern(detector_group_2, 'left_tubes', 1100000, [-0.5192 - 1.1, -0.48195, 4.0],
                                            [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]),
                                            depends_on=sample_position)
    builder.add_tube_pixel(left_tubes_2, 0.002033984375, 0.00405)
    right_tubes_2 = builder.add_grid_pattern(detector_group_2, 'right_tubes', 1101000, [-0.5222 - 1.1, -0.473855, 4.0],
                                             [512, 60], [1, 2000], ([0.002033984375, 0, 0], [0, 0.0162, 0]),
                                             depends_on=sample_position)
    builder.add_tube_pixel(right_tubes_2, 0.002033984375, 0.00405)

    # Copy data from the existing NeXus file and add some other bits to flesh out the example file
    builder.add_user('Sans2d Team', 'ISIS, STFC')
    # Define monitor_1 to have the shape of the Utah teapot as example use of NXshape
    builder.add_shape_from_file('teapot.off', 'instrument/monitor1', 'shape')
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
                                    ('raw_data_1/definition', 'raw_data_1/definition'),
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

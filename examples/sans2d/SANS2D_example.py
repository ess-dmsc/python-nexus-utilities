from collections import OrderedDict
from nexusutils.nexusbuilder import NexusBuilder
from nexusutils.detectorplotter import DetectorPlotter
from nexusutils.nxloghelper import add_example_nxlog


def __copy_and_truncate(builder, source_dataset_path, target_dataset_path, truncate_to_size):
    """
    Copy data from the existing NeXus file, but truncate datasets to specified length
    """
    source_dataset = builder.source_file.get(source_dataset_path)[:truncate_to_size]
    source_attrs = builder.source_file.get(source_dataset_path).attrs
    if target_dataset_path[0] == "/":
        target_dataset_path = target_dataset_path[0:]
    target_parent_path = "".join(target_dataset_path.split('/')[1:-1])
    target_dataset_name = target_dataset_path.split('/')[-1]
    builder.add_dataset(builder.get_root()[target_parent_path], target_dataset_name, source_dataset,
                        attributes=source_attrs)


def __copy_existing_data():
    """
    Copy data from the existing NeXus file to flesh out the example file
    """
    builder.add_user('Sans2d Team', 'ISIS, STFC')
    builder.copy_items(OrderedDict([('raw_data_1/instrument/moderator', nx_entry_name + '/instrument/moderator'),
                                    ('raw_data_1/instrument/moderator/distance',
                                     nx_entry_name + '/instrument/moderator/distance'),
                                    ('raw_data_1/instrument/source/probe',
                                     nx_entry_name + '/instrument/source/probe'),
                                    ('raw_data_1/instrument/source/type', nx_entry_name + '/instrument/source/type'),
                                    ('raw_data_1/sample/name', nx_entry_name + '/sample/name'),
                                    ('raw_data_1/sample/type', nx_entry_name + '/sample/type'),
                                    ('raw_data_1/duration', nx_entry_name + '/duration'),
                                    ('raw_data_1/start_time', nx_entry_name + '/start_time'),
                                    ('raw_data_1/end_time', nx_entry_name + '/end_time'),
                                    ('raw_data_1/run_cycle', nx_entry_name + '/run_cycle'),
                                    ('raw_data_1/title', nx_entry_name + '/title'),
                                    ('raw_data_1/monitor_1/data', nx_entry_name + '/instrument/monitor1/data'),
                                    ('raw_data_1/monitor_1/time_of_flight',
                                     nx_entry_name + '/instrument/monitor1/time_of_flight'),
                                    ('raw_data_1/monitor_2/data', nx_entry_name + '/instrument/monitor2/data'),
                                    ('raw_data_1/monitor_2/time_of_flight',
                                     nx_entry_name + '/instrument/monitor2/time_of_flight'),
                                    ('raw_data_1/monitor_3/data', nx_entry_name + '/instrument/monitor3/data'),
                                    ('raw_data_1/monitor_3/time_of_flight',
                                     nx_entry_name + '/instrument/monitor3/time_of_flight'),
                                    ('raw_data_1/monitor_4/data', nx_entry_name + '/instrument/monitor4/data'),
                                    ('raw_data_1/monitor_4/time_of_flight',
                                     nx_entry_name + '/instrument/monitor4/time_of_flight'),
                                    ]))


if __name__ == '__main__':
    output_filename = 'SANS2D_example.hdf5'
    nx_entry_name = 'entry'
    # compress_type=32001 for BLOSC, or don't specify compress_type and opts to get non-compressed datasets
    with NexusBuilder(output_filename, input_nexus_filename='SANS_test.nxs', nx_entry_name=nx_entry_name,
                      idf_file='SANS2D_Definition_Tubes.xml', compress_type='gzip', compress_opts=1) as builder:
        builder.add_instrument_geometry_from_idf()

        # Define monitor_1 to have the shape of the Utah teapot as example use of NXshape
        builder.add_shape_from_file('../off_files/teapot.off', 'instrument/monitor1', 'shape')

        __copy_existing_data()

        builder.add_nx_group(builder.get_root(), 'detector_1_events', 'NXevent_data')

        __copy_and_truncate(builder, 'raw_data_1/detector_1_events/event_id', 'raw_data_1/detector_1_events/event_id',
                            7014)
        __copy_and_truncate(builder, 'raw_data_1/detector_1_events/event_index',
                            'raw_data_1/detector_1_events/event_index', 10)
        __copy_and_truncate(builder, 'raw_data_1/detector_1_events/event_time_zero',
                            'raw_data_1/detector_1_events/event_time_zero', 7014)
        __copy_and_truncate(builder, 'raw_data_1/detector_1_events/event_time_offset',
                            'raw_data_1/detector_1_events/event_time_offset', 10)

        add_example_nxlog(builder, '/' + nx_entry_name + '/sample/', 10)

    with DetectorPlotter(output_filename, nx_entry_name) as plotter:
        plotter.plot_pixel_positions()

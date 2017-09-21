from nexusbuilder import NexusBuilder
import numpy as np
from datetime import datetime

if __name__ == '__main__':
    output_filename = 'SANS2D_scan_example.hdf5'
    # compress_type=32001 for BLOSC, or don't specify compress_type and opts to get non-compressed datasets
    builder = NexusBuilder(output_filename, input_nexus_filename='SANS_test.nxs',
                           idf_file='SANS2D_Definition_Tubes.xml', compress_type='gzip', compress_opts=1)

    builder.add_instrument_geometry_from_idf()

    # Add an NXtransformation for a scan of the front-detector panel position

    # Panel moves 0.6 metres with 4 scan intervals
    scan_positions = np.array([0., 0., .2, .2, .4, .4, .6, .6])
    scan_units = 'm'
    # At each position data is recorded for 5 minutes
    # and there is a 30 second gap between each interval for the detector to move
    # For example the detector moves from 0.0 to 0.2 during 300 to 330 seconds
    scan_times = np.array([0., 300., 330., 630., 660., 960., 990., 1290.])
    scan_time_units = 's'
    # Our initial location will be the default location of the panel which was recorded from the IDF
    initial_location = '/raw_data_1/instrument/detector_1/location'
    vector = [1., 0., 0.]  # Move the panel along x axis: horizontal and perpendicular to beam direction
    builder.add_nx_log('/raw_data_1/instrument/detector_1/transformations', 'translation_scan', datetime.now(),
                       scan_positions, scan_times, scan_units,
                       scan_time_units, log_attributes={'vector': vector, 'depends_on': initial_location,
                                                        'transformation_type': 'translation'})
    builder.delete_dataset_or_group('/raw_data_1/instrument/detector_1/depends_on')
    builder.add_dataset('/raw_data_1/instrument/detector_1', 'depends_on',
                        '/raw_data_1/instrument/detector_1/transformations/translation_scan')

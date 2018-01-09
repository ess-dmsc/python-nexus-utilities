from nexusbuilder import NexusBuilder
from detectorplotter import DetectorPlotter

if __name__ == '__main__':
    output_filename = 'LOKI_example_gzip.hdf5'
    with NexusBuilder(output_filename, idf_file='LOKI_Definition.xml',
                      compress_type='gzip', compress_opts=1) as builder:
        builder.add_instrument_geometry_from_idf()

        # A few more details to flesh out the example
        builder.add_user('LOKI Team', 'ESS')
        builder.add_dataset('/raw_data_1/', 'definition', 'TOFRAW',
                            {'url': 'http://definition.nexusformat.org/instruments/TOFRAW?version=1.0'})

    with DetectorPlotter(output_filename) as plotter:
        plotter.plot_pixel_positions()

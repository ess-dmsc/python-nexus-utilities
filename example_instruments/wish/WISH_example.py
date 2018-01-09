from nexusbuilder import NexusBuilder
from detectorplotter import DetectorPlotter

if __name__ == '__main__':
    output_filename = 'WISH_example_gzip_compress.hdf5'

    with NexusBuilder(output_filename, idf_file='WISH_Definition_10Panels.xml',
                      compress_type='gzip', compress_opts=1) as builder:
        builder.add_instrument_geometry_from_idf()

    plotter = DetectorPlotter(output_filename)
    plotter.plot_pixel_positions()

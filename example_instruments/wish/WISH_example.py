from nexusbuilder import NexusBuilder
from detectorplotter import DetectorPlotter

if __name__ == '__main__':
    output_filename = 'WISH_example_gzip_compress.hdf5'

    builder = NexusBuilder(output_filename, idf_file='WISH_Definition_10Panels.xml',
                           compress_type='gzip', compress_opts=1)
    builder.add_instrument_geometry_from_idf()
    del builder  # file is closed in the builder destructor

    plotter = DetectorPlotter(output_filename)
    plotter.plot_pixel_positions()

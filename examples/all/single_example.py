from nexusbuilder import NexusBuilder
from detectorplotter import DetectorPlotter

instrument_name = 'SANS2D'
output_filename = instrument_name + '_Definition.hdf5'
builder = NexusBuilder(output_filename, idf_file=instrument_name + '_Definition.xml',
                       compress_type='gzip', compress_opts=1)
builder.add_instrument_geometry_from_idf()

del builder

plotter = DetectorPlotter(output_filename)
plotter.plot_pixel_positions()

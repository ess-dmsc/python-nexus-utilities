from nexusutils.nexusbuilder import NexusBuilder
from nexusutils.drawoff import render_off_from_file
from nexusutils.nexustooff import nexus_geometry_to_off_file

if __name__ == '__main__':
    output_filename = 'example_nx_geometry.nxs'
    with NexusBuilder(output_filename, idf_file='small_tube_pixel_detector.xml', compress_type='gzip',
                      compress_opts=1) as builder:
        builder.add_instrument_geometry_from_idf()

        # Define sample to have the shape of the Utah teapot as example use of NXoff_geometry
        builder.add_shape_from_file('../off_files/teapot.off', 'sample', 'shape')

    output_off_file = "off_and_cylinder.off"
    nexus_geometry_to_off_file(output_filename, output_off_file)
    render_off_from_file(output_off_file)

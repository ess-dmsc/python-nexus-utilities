from nexusutils.nexusbuilder import NexusBuilder

if __name__ == '__main__':
    output_filename = 'SMALLFAKE_example_geometry.hdf5'
    # compress_type=32001 for BLOSC, or don't specify compress_type and opts to get non-compressed datasets
    with NexusBuilder(output_filename, idf_file='SMALLFAKE_Definition.xml', compress_type='gzip',
                      compress_opts=1) as builder:
        builder.add_instrument_geometry_from_idf()
        builder.add_shape_from_file('../off_files/cube.off', 'instrument/monitor1', 'shape')

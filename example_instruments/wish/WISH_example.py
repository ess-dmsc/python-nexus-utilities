from nexusbuilder import NexusBuilder

if __name__ == '__main__':
    builder = NexusBuilder('WISH_example_gzip_compress.hdf5', idf_file='WISH_Definition_10Panels.xml',
                           compress_type='gzip', compress_opts=1)

    builder.add_instrument_geometry_from_idf()

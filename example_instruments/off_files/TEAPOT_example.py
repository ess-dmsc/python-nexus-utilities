from nexusbuilder import NexusBuilder

output_filename = 'example_nx_geometry.nxs'
with NexusBuilder(output_filename, compress_type='gzip', compress_opts=1) as builder:
    instrument_group = builder.add_instrument("TEAPOT")
    builder.add_shape_from_file("teapot.off", instrument_group, "shape")
    # Add an icosahedral sample
    sample_group = builder.add_sample("sample")
    builder.add_shape_from_file("icosa.off", sample_group, "shape")

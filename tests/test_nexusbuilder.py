import numpy as np
from nexusutils.nexusbuilder import NexusBuilder


def test_add_instrument_results_in_instrument_in_file_with_specified_name():
    builder = NexusBuilder('test_output_file.hdf5', file_in_memory=True)
    instrument_name = 'TEST'
    builder.add_instrument(instrument_name)
    root = builder.get_root()
    instrument_group = root['instrument']
    assert instrument_group['name'][...].astype(str) == instrument_name


def test_add_source_results_in_source_in_file_with_specified_name():
    builder = NexusBuilder('test_output_file.hdf5', file_in_memory=True)
    source_name = 'TEST_SOURCE'
    builder.add_instrument('TEST')
    builder.add_source(source_name)
    root = builder.get_root()
    source_group = root['instrument/source']
    assert source_group['name'][...].astype(str) == source_name

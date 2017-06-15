import env
import pytest
from nexusbuilder import NexusBuilder


def test_add_instrument():
    builder = NexusBuilder('test_output_file.hdf5', file_in_memory=True)
    builder.add_instrument('TEST')


def test_add_source():
    builder = NexusBuilder('test_output_file.hdf5', file_in_memory=True)
    builder.add_instrument('TEST')
    builder.add_source('TEST_SOURCE')


def test_add_sample():
    builder = NexusBuilder('test_output_file.hdf5', file_in_memory=True)
    builder.add_instrument('TEST')
    builder.add_sample([0.0, -0.37, 4.2])

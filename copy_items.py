import h5py
from collections import OrderedDict
import tables
import os
import logging

"""
Functions to assist with building example NeXus files from existing ones

NB. tables import looks redundant but actually loads BLOSC compression filter
"""

logger = logging.getLogger('NeXus_utils')
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)


def wipe_file(filename):
    with h5py.File(filename, 'w') as f_write:
        pass


def copy_group(source_file, target_file, source_group_name, target_group_name):
    """
    Copy a group with its attributes but without members
    
    :param source_file: Copy group from source_file object
    :param target_file: Copy group to target_file object
    :param source_group_name: Name of group in source file
    :param target_group_name: Name of group in target file
    """
    target_file.copy(source_file[source_group_name], source_group_name, shallow=True)
    for sub_group in source_file[source_group_name].keys():
        if sub_group in target_file[target_group_name]:
            target_file[target_group_name].__delitem__(sub_group)


def copy_dataset(data_1, f_write, target_dataset, compress_type, compress_opts):
    """
    Copy a dataset with specified compression options and the source dataset's attributes
    
    :param compress_opts: Compression options, for example gzip compression level
    :param compress_type: Name or id of compression filter https://support.hdfgroup.org/services/contributions.html
    :param data_1: The dataset being copied
    :param f_write: File object for the target file
    :param target_dataset: Name of the dataset in the target file
    """
    try:
        d_set = f_write.create_dataset(target_dataset, data_1[...].shape, compression=compress_type,
                                       compression_opts=compress_opts)
        d_set[...] = data_1[...]
    except TypeError:
        # probably this is a scalar dataset so just write it without compression
        # abusing try-except...
        f_write[target_dataset] = data_1[...]
    # Now copy attributes
    source_attributes = data_1.attrs.items()
    target_attributes = f_write[target_dataset].attrs
    for key, value in source_attributes:
        if key != 'target':
            logger.debug('attr key: ' + str(key) + ' value: ' + str(value))
            target_attributes.create(key, value)


def copy_items(source_file_name, target_file_name, dataset_map, compress_type=32001, compress_opts=None):
    """
    Copy datasets and groups from one NeXus file to another
    Datasets in the output file are written with the specified compression
    
    :param source_file_name: Name of the input file
    :param target_file_name: Name of the output file
    :param dataset_map: Input groups and datasets to output ones, order must be top-down in hierarchy of output file 
                        Must be ordered.
    :param compress_type: Name or id of compression filter https://support.hdfgroup.org/services/contributions.html
    :param compress_opts: Compression options, for example gzip compression level
    """
    if not isinstance(dataset_map, OrderedDict):
        raise Exception(
            'Map of source and target items but be an OrderedDict in top-down hierarchy order of the target file')

    with h5py.File(source_file_name, 'r') as f_read:
        for source_item, target_item in dataset_map.items():
            data_1 = f_read.get(source_item)
            with h5py.File(target_file_name, 'r+') as f_write:
                if isinstance(data_1, h5py.Dataset):
                    copy_dataset(data_1, f_write, target_item, compress_type, compress_opts)
                elif isinstance(data_1, h5py.Group):
                    copy_group(f_read, f_write, source_item, target_item)

import h5py
import logging
from collections import OrderedDict
import tables
import os

logger = logging.getLogger('NeXus_Builder')
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)


class NexusBuilder:
    """
    Assists with building example NeXus files in prototype ESS format from existing files from other institutions

    NB. tables import looks redundant but actually loads BLOSC compression filter
    """

    def __init__(self, source_file_name, target_file_name, compress_type=None, compress_opts=None):
        """
        compress_type=32001 for BLOSC
        
        :param source_file_name: Name of the input file
        :param target_file_name: Name of the output file
        :param compress_type: Name or id of compression filter https://support.hdfgroup.org/services/contributions.html
        :param compress_opts: Compression options, for example gzip compression level
        """
        self.compress_type = compress_type
        self.compress_opts = compress_opts
        self.__wipe_file(target_file_name)
        self.source_file = h5py.File(source_file_name, 'r')
        self.target_file = h5py.File(target_file_name, 'r+')

    def copy_items(self, dataset_map):
        """
        Copy datasets and groups from one NeXus file to another

        :param dataset_map: Input groups and datasets to output ones, order must be top-down in hierarchy of output file 
                            Must be ordered.
        """
        if not isinstance(dataset_map, OrderedDict):
            raise Exception(
                'Map of source and target items but be an OrderedDict in top-down hierarchy order of the target file')

        for source_item_name, target_item_name in dataset_map.items():
            source_item = self.source_file.get(source_item_name)
            if isinstance(source_item, h5py.Dataset):
                self.__copy_dataset(source_item, target_item_name)
            elif isinstance(source_item, h5py.Group):
                self.__copy_group(source_item_name, target_item_name)

    def __del__(self):
        self.source_file.close()
        self.target_file.close()

    @staticmethod
    def __wipe_file(filename):
        with h5py.File(filename, 'w') as f_write:
            pass

    def __copy_group(self, source_group_name, target_group_name):
        """
        Copy a group with its attributes but without members
    
        :param source_group_name: Name of group in source file
        :param target_group_name: Name of group in target file
        """
        self.target_file.copy(self.source_file[source_group_name], source_group_name, shallow=True)
        for sub_group in self.source_file[source_group_name].keys():
            if sub_group in self.target_file[target_group_name]:
                self.target_file[target_group_name].__delitem__(sub_group)

    def __copy_dataset(self, dataset, target_dataset):
        """
        Copy a dataset with specified compression options and the source dataset's attributes
    
        :param dataset: The dataset being copied
        :param target_dataset: Name of the dataset in the target file
        """
        try:
            d_set = self.target_file.create_dataset(target_dataset, dataset[...].shape, compression=self.compress_type,
                                                    compression_opts=self.compress_opts)
            d_set[...] = dataset[...]
        except TypeError:
            # probably this is a scalar dataset so just write it without compression
            # abusing try-except...
            self.target_file[target_dataset] = dataset[...]
        # Now copy attributes
        source_attributes = dataset.attrs.items()
        target_attributes = self.target_file[target_dataset].attrs
        for key, value in source_attributes:
            if key != 'target':
                logger.debug('attr key: ' + str(key) + ' value: ' + str(value))
                target_attributes.create(key, value)

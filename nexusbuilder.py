import h5py
import logging
from collections import OrderedDict
import tables
import os
import numpy as np
from idfparser import IDFParser

logger = logging.getLogger('NeXus_Builder')
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)


def is_scalar(object_to_check):
    if hasattr(object_to_check, "__len__"):
        return len(object_to_check) == 1
    return True


class NexusBuilder:
    """
    Assists with building example NeXus files in prototype ESS format from existing files from other institutions

    NB. tables import looks redundant but actually loads BLOSC compression filter
    """

    def __init__(self, source_file_name, target_file_name, compress_type=None, compress_opts=None,
                 nx_entry_name='raw_data_1', idf_filename=None):
        """
        compress_type=32001 for BLOSC
        
        :param source_file_name: Name of the input file
        :param target_file_name: Name of the output file
        :param nx_entry_name: Name of the root group (NXentry class)
        :param compress_type: Name or id of compression filter https://support.hdfgroup.org/services/contributions.html
        :param compress_opts: Compression options, for example gzip compression level
        :param idf_filename: Filename of a Mantid IDF file from which to get instrument geometry
        """
        self.compress_type = compress_type
        self.compress_opts = compress_opts
        self.__wipe_file(target_file_name)
        self.source_file = h5py.File(source_file_name, 'r')
        self.target_file = h5py.File(target_file_name, 'r+')
        # Having an NXentry root group is compulsory in NeXus standard
        self.root = self.__add_nx_entry(nx_entry_name)
        if idf_filename:
            self.idf_parser = IDFParser(idf_filename)
        else:
            self.idf_parser = None

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

    def add_user(self, name, affiliation):
        """
        Add an NXuser
        
        :param name: Name of the user 
        :param affiliation: Affiliation of the user
        :return: 
        """
        user_group = self.__add_nx_group(self.root, 'user_1', 'NXuser')
        user_group.create_dataset('name', data=name)
        user_group.create_dataset('affiliation', data=affiliation)

    def add_detector_banks_from_idf(self):
        """
        Add detector banks from a Mantid IDF file
        NB, currently only works for "RectangularDetector" panels 
        """
        if self.idf_parser is None:
            logger.error('No IDF file was given to the NexusBuilder, cannot call add_detector_banks_from_idf')
        for det_info in self.idf_parser.get_detector_banks():
            det_bank_group = self.add_detector_bank(det_info['name'], det_info['number'], det_info['x_pixel_size'],
                                                    det_info['y_pixel_size'], det_info['thickness'],
                                                    det_info['distance'][2], det_info['distance'][0],
                                                    det_info['distance'][1],
                                                    det_info['x_pixel_offset'], det_info['y_pixel_offset'])
            if 'transformation' in det_info:
                self.__add_translation(det_bank_group, det_info['transformation'])

    def add_detector_bank(self, name, number, x_pixel_size, y_pixel_size, thickness, distance, x_beam_centre,
                          y_beam_centre, x_pixel_offset=None, y_pixel_offset=None):
        """
        Add an NXdetector, only suitable for rectangular detectors of consistent pixels
        
        :param name: Name of the detector panel
        :param number : Banks are numbered from 1
        :param x_pixel_size: Pixel width
        :param y_pixel_size: Pixel height
        :param thickness: Pixel thickness
        :param distance: Bank distance along z from parent component
        :param x_beam_centre: Displacement of the centre of the bank from the beam centre along x
        :param y_beam_centre: Displacement of the centre of the bank from the beam centre along y
        :param x_pixel_offset: Pixel offsets on x axis from centre of detector
        :param y_pixel_offset: Pixel offsets on y axis from centre of detector
        :return: NXdetector group
        """
        # TODO add pixel_numbers (ids)
        if not is_scalar(x_pixel_size):
            logger.error('In NexusBuilder.__add_detector_bank x_pixel_size must be scalar')
        if not is_scalar(y_pixel_size):
            logger.error('In NexusBuilder.__add_detector_bank y_pixel_size must be scalar')
        if not is_scalar(thickness):
            logger.error('In NexusBuilder.__add_detector_bank thickness must be scalar')
        instrument_group = self.root['instrument']
        detector_bank_group = self.__add_nx_group(instrument_group, 'detector_' + str(number), 'NXdetector')
        detector_bank_group.create_dataset('local_name', data=name)
        thickness_dataset = detector_bank_group.create_dataset('sensor_thickness', data=np.array([thickness]))
        thickness_dataset.attrs.create('units', 'metres')
        distance_dataset = detector_bank_group.create_dataset('distance', data=np.array([distance]))
        distance_dataset.attrs.create('units', 'metres')
        self.__add_detector_bank_axis(detector_bank_group, 'x', x_pixel_size, x_pixel_offset, x_beam_centre)
        self.__add_detector_bank_axis(detector_bank_group, 'y', y_pixel_size, y_pixel_offset, y_beam_centre)
        return detector_bank_group

    def __add_detector_bank_axis(self, group, axis, pixel_size, pixel_offset, beam_centre):
        pixel_size_dataset = group.create_dataset(axis + '_pixel_size', data=np.array([pixel_size]))
        pixel_size_dataset.attrs.create('units', 'metres')
        beam_centre_dataset = group.create_dataset('beam_center_' + axis, data=np.array([beam_centre]))
        beam_centre_dataset.attrs.create('units', 'metres')
        if pixel_offset is not None:
            pixel_offset_dataset = group.create_dataset(axis + '_pixel_offset', data=pixel_offset,
                                                        compression=self.compress_type,
                                                        compression_opts=self.compress_opts)
            pixel_offset_dataset.attrs.create('units', 'metres')

    def __del__(self):
        self.source_file.close()
        self.target_file.close()

    def __add_translation(self, group, transformation_info):
        # TODO finish (add datasets)
        self.__add_nx_group(group, 'transformation', 'NXtransformation')

    def __add_nx_entry(self, nx_entry_name):
        entry_group = self.target_file.create_group(nx_entry_name)
        entry_group.attrs.create('NX_class', 'NXentry')
        return entry_group

    @staticmethod
    def __add_nx_group(parent_group, group_name, nx_class_name):
        created_group = parent_group.create_group(group_name)
        created_group.attrs.create('NX_class', nx_class_name)
        return created_group

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
        self.target_file.copy(self.source_file[source_group_name], target_group_name, shallow=True)
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
            d_set = self.target_file.create_dataset(target_dataset, dataset[...].shape, dtype=dataset.dtype,
                                                    compression=self.compress_type, compression_opts=self.compress_opts)
            d_set[...] = dataset[...]
        except TypeError:
            logger.error('Type error copying to dataset: ' + target_dataset + ', value is type: ' + str(
                dataset.dtype))
        except IOError as e:
            logger.error('IO error copying to dataset: ' + target_dataset + ', value is type: ' + str(
                dataset.dtype) + ', errorstr: ' + e.strerror)
        except:
            logger.error('Unexpected error in NexusBuilder.__copy_dataset')
            raise
        # Now copy attributes
        source_attributes = dataset.attrs.items()
        target_attributes = self.target_file[target_dataset].attrs
        for key, value in source_attributes:
            if key != 'target':
                logger.debug('attr key: ' + str(key) + ' value: ' + str(value))
                target_attributes.create(key, value)

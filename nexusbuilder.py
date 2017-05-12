import h5py
import logging
from collections import OrderedDict
import tables
import os
import xml.etree.ElementTree
import numpy as np

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

    def __init__(self, source_file_name, target_file_name, compress_type=None, compress_opts=None,
                 nx_entry_name='raw_data_1'):
        """
        compress_type=32001 for BLOSC
        
        :param source_file_name: Name of the input file
        :param target_file_name: Name of the output file
        :param nx_entry_name: Name of the root group (NXentry class)
        :param compress_type: Name or id of compression filter https://support.hdfgroup.org/services/contributions.html
        :param compress_opts: Compression options, for example gzip compression level
        """
        self.compress_type = compress_type
        self.compress_opts = compress_opts
        self.__wipe_file(target_file_name)
        self.source_file = h5py.File(source_file_name, 'r')
        self.target_file = h5py.File(target_file_name, 'r+')
        # Having an NXentry root group is compulsory in NeXus standard
        self.root = self.__add_nx_entry(nx_entry_name)

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

    def add_detector_banks(self, mantid_idf):
        """
        Add detector banks from a Mantid IDF file
        NB, currently only works for "RectangularDetector" panels
        
        :param mantid_idf: filename of the Mantid IDF XML file 
        """
        root = xml.etree.ElementTree.parse(mantid_idf).getroot()
        ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}
        # Our root should be the instrument
        assert (root.tag == '{' + ns['d'] + '}instrument')

        # Look for detector bank definition
        for xml_type in root.findall('d:type', ns):
            if xml_type.get('is') == 'rectangular_detector':
                x_pixel_size, y_pixel_size, thickness = self.__get_pixel(root, xml_type.get('type'))
                bank_type_name = xml_type.get('name')
                x_pixel_offset_1d = self.__get_1d_pixel_offsets('x', xml_type)
                y_pixel_offset_1d = self.__get_1d_pixel_offsets('y', xml_type)
                x_pixel_offset, y_pixel_offset = np.meshgrid(x_pixel_offset_1d, y_pixel_offset_1d)
                for component in root.findall('d:component', ns):
                    if component.get('type') == bank_type_name:
                        bank_name = component.find('d:location', ns).get('name')
                        # TODO translate the pixel offsets by the bank location
                        # Or should add an NXtransformation for that?
                        # TODO also get the pixel id information (detector_number)
                        location = component.find('d:location', ns)
                        translation_list = np.array([location.get('x'), location.get('y'), location.get('z')])
                        translation = np.array(map(lambda x: 0 if x is None else x, translation_list))
                        self.__add_detector_bank(bank_name, x_pixel_size, y_pixel_size, thickness)

    @staticmethod
    def __get_1d_pixel_offsets(dimension_name, xml_type):
        step = float(xml_type.get(dimension_name + 'step'))
        pixels = int(xml_type.get(dimension_name + 'pixels'))
        start = float(xml_type.get(dimension_name + 'start'))
        stop = start + (step * pixels)
        return np.linspace(start, stop, pixels)

    def __del__(self):
        self.source_file.close()
        self.target_file.close()

    def __add_detector_bank(self, name, x_pixel_size, y_pixel_size, thickness):
        instrument_group = self.root['instrument']
        detector_bank_group = self.__add_nx_group(instrument_group, name, 'NXdetector')

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

    @staticmethod
    def __get_point(xml_point):
        return np.array([xml_point.get('x'), xml_point.get('y'), xml_point.get('z')]).astype(float)

    def __get_pixel(self, xml_root, type_name):
        ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}
        for type in xml_root.findall('d:type', ns):
            if type.get('name') == type_name and type.get('is') == 'detector':
                cuboid = type.find('d:cuboid', ns)
                if cuboid is not None:
                    left_front_bottom = self.__get_point(cuboid.find('d:left-front-bottom-point', ns))
                    left_front_top = self.__get_point(cuboid.find('d:left-front-top-point', ns))
                    left_back_bottom = self.__get_point(cuboid.find('d:left-back-bottom-point', ns))
                    right_front_bottom = self.__get_point(cuboid.find('d:right-front-bottom-point', ns))
                    # Assume thickness is front to back
                    front_to_back = left_back_bottom - left_front_bottom
                    thickness = np.sqrt(np.dot(front_to_back, front_to_back))
                    # Assume x pixel size is left to right
                    left_to_right = right_front_bottom - left_front_bottom
                    x_pixel_size = np.sqrt(np.dot(left_to_right, left_to_right))
                    # Assume y pixel size is top to bottom
                    top_to_bottom = left_front_top - left_front_bottom
                    y_pixel_size = np.sqrt(np.dot(top_to_bottom, top_to_bottom))
                    return x_pixel_size, y_pixel_size, thickness
                else:
                    print('no cuboid shape found to define pixel')
        return None, None, None

import h5py
import logging
from collections import OrderedDict
import tables
import os
import numpy as np
from idfparser import IDFParser
import nexusutils

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
        nexusutils.wipe_file(target_file_name)
        self.source_file = h5py.File(source_file_name, 'r')
        self.target_file = h5py.File(target_file_name, 'r+')
        # Having an NXentry root group is compulsory in NeXus format
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
                'Map of source and target items must be an OrderedDict in top-down hierarchy order of the target file')

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
        user_group = nexusutils.add_nx_group(self.root, 'user_1', 'NXuser')
        user_group.create_dataset('name', data=name)
        user_group.create_dataset('affiliation', data=affiliation)

    def add_detector_banks_from_idf(self):
        """
        Add detector banks from a Mantid IDF file
        NB, currently only works for "RectangularDetector" panels 
            currently assumes the coordinate system in the IDF is the same as the NeXus one
            (z is beam direction, x is the other horizontal, y is vertical)
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
                nexusutils.add_translation(det_bank_group, det_info['transformation'])

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
        if not nexusutils.is_scalar(x_pixel_size):
            logger.error('In NexusBuilder.__add_detector_bank x_pixel_size must be scalar')
        if not nexusutils.is_scalar(y_pixel_size):
            logger.error('In NexusBuilder.__add_detector_bank y_pixel_size must be scalar')
        if not nexusutils.is_scalar(thickness):
            logger.error('In NexusBuilder.__add_detector_bank thickness must be scalar')
        instrument_group = self.root['instrument']
        detector_bank_group = nexusutils.add_nx_group(instrument_group, 'detector_' + str(number), 'NXdetector')
        detector_bank_group.create_dataset('local_name', data=name)
        thickness_dataset = detector_bank_group.create_dataset('sensor_thickness', data=np.array([thickness]))
        thickness_dataset.attrs.create('units', 'metres')
        distance_dataset = detector_bank_group.create_dataset('distance', data=np.array([distance]))
        distance_dataset.attrs.create('units', 'metres')
        self.__add_detector_bank_axis(detector_bank_group, 'x', x_pixel_size, x_pixel_offset, x_beam_centre)
        self.__add_detector_bank_axis(detector_bank_group, 'y', y_pixel_size, y_pixel_offset, y_beam_centre)
        return detector_bank_group

    def add_detector(self, name, number):
        """
        Add an NXdetector with minimal details
        :param name: Name of the detector panel
        :param number: Detectors are typically numbered from 1
        :return: NXdetector group
        """
        instrument_group = self.root['instrument']
        detector_group = nexusutils.add_nx_group(instrument_group, 'detector_' + str(number), 'NXdetector')
        detector_group.create_dataset('local_name', data=name)
        return detector_group

    def add_tube_pixel(self):
        pass

    @staticmethod
    def add_grid_pattern(detector_group, name, id_start, position_start, size, id_steps, steps):
        """
        Add an NXgrid_pattern
        NB, will need to add a pixel_shape definition to it afterwards

        :param detector_group: NXdetector group to add grid pattern to
        :param name: Name of the NXgrid_pattern group
        :param id_start: The lowest detector id in the grid
        :param position_start: Vector defining the position of the detector pixel with the lowest id
        :param size: Iterable containing the number of pixels in each dimension of the grid
        :param id_steps: Iterable of scalars defining increase in id number along each grid dimension
        :param steps: Iterable of vectors defining translation along each grid dimension to get to next pixel
        :return: NXgrid_pattern group
        """
        grid_pattern = nexusutils.add_nx_group(detector_group, name, 'NXgrid_pattern')
        grid_pattern.create_dataset('id_start', data=np.array([id_start]))
        position_start_dataset = grid_pattern.create_dataset('position_start', data=np.array([position_start]))
        position_start_dataset.attrs.create('units', np.array('metres').astype('|S6'))
        grid_pattern.create_dataset('size', data=np.array([size]))
        grid_pattern.create_dataset('X_id_step', data=np.array([id_steps[0]]))
        grid_pattern.create_dataset('Y_id_step', data=np.array([id_steps[1]]))
        if len(id_steps) > 2:
            grid_pattern.create_dataset('Z_id_step', data=np.array([id_steps[2]]))
        X_step_dataset = grid_pattern.create_dataset('X_step', data=np.array([steps[0]]))
        X_step_dataset.attrs.create('units', np.array('metres').astype('|S6'))
        Y_step_dataset = grid_pattern.create_dataset('Y_step', data=np.array([steps[1]]))
        Y_step_dataset.attrs.create('units', np.array('metres').astype('|S6'))
        if len(steps) > 2:
            Z_step_dataset = grid_pattern.create_dataset('Z_step', data=np.array([steps[2]]))
            Z_step_dataset.attrs.create('units', np.array('metres').astype('|S6'))
        return grid_pattern

    @staticmethod
    def __add_pixel_direction(detector_module, name, pixel_direction_offset, pixel_direction_step,
                              direction_size):
        if all(arg is not None for arg in [name, pixel_direction_offset, pixel_direction_step, direction_size]):
            if len(pixel_direction_offset) != 3:
                logger.error(
                    'In add_detector_module the pixel direction offset' +
                    ' must each have three values (corresponding to the cartesian axes)' +
                    ' Module name: ' + name)
            pixel_direction = detector_module.create_dataset(name, shape=[0])
            pixel_direction.attrs.create('transformation_type', np.array('translation').astype('|S11'))
            pixel_direction.attrs.create('offset_units', np.array('metres').astype('|S6'))
            pixel_direction.attrs.create('offset', data=np.array(pixel_direction_offset))
            pixel_direction.attrs.create('size_in_pixels', direction_size)
            pixel_direction.attrs.create('pixel_number_step', pixel_direction_step)
        else:
            logger.debug('Missing arguments in __add_pixel_direction to define direction: ' + name)

    def __add_detector_bank_axis(self, group, axis, pixel_size, pixel_offset, beam_centre):
        pixel_size_dataset = group.create_dataset(axis + '_pixel_size', data=np.array([pixel_size]))
        pixel_size_dataset.attrs.create('units', np.array('metres').astype('|S6'))
        beam_centre_dataset = group.create_dataset('beam_center_' + axis, data=np.array([beam_centre]))
        beam_centre_dataset.attrs.create('units', np.array('metres').astype('|S6'))
        if pixel_offset is not None:
            pixel_offset_dataset = group.create_dataset(axis + '_pixel_offset', data=pixel_offset,
                                                        compression=self.compress_type,
                                                        compression_opts=self.compress_opts)
            pixel_offset_dataset.attrs.create('units', np.array('metres').astype('|S6'))

    def __del__(self):
        # Wrap in try to ignore exception which h5py likes to throw with Python 3.5
        try:
            self.source_file.close()
            self.target_file.close()
        except Exception:
            pass

    def __add_nx_entry(self, nx_entry_name):
        entry_group = self.target_file.create_group(nx_entry_name)
        entry_group.attrs.create('NX_class', np.array('NXentry').astype('|S7'))
        return entry_group

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

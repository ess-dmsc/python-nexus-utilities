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
        NB, the order is important as the method of copying groups used deletes any sub-groups and datasets.

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
        :return: NXuser
        """
        user_group = nexusutils.add_nx_group(self.root, 'user_1', 'NXuser')
        user_group.create_dataset('name', data=name)
        user_group.create_dataset('affiliation', data=affiliation)
        return user_group

    def add_dataset(self, group, name, data, attributes=None):
        """
        Add a dataset to a given group

        :param group: Group object, or group path from NXentry as a string
        :param name: Name of the dataset to create
        :param data: Data to put in the dataset
        :param attributes: Optional dictionary of attributes to add to dataset
        :return: Dataset
        """
        if isinstance(group, str):
            group = self.root[group]
        if nexusutils.is_scalar(data):
            # Don't try to use compression with scalar datasets
            data = [data]
            dataset = group.create_dataset(name, data=data)
        else:
            dataset = group.create_dataset(name, data=data, compression=self.compress_type,
                                           compression_opts=self.compress_opts)

        if attributes:
            for key in attributes:
                if isinstance(attributes[key], str):
                    # Since python 3 we have to treat strings like this
                    dataset.attrs.create(key, np.array(attributes[key]).astype('|S' + str(len(attributes[key]))))
                else:
                    dataset.attrs.create(key, np.array(attributes[key]))
        return dataset

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
            logger.error('In NexusBuilder.add_detector_bank x_pixel_size must be scalar')
        if not nexusutils.is_scalar(y_pixel_size):
            logger.error('In NexusBuilder.add_detector_bank y_pixel_size must be scalar')
        if not nexusutils.is_scalar(thickness):
            logger.error('In NexusBuilder.add_detector_bank thickness must be scalar')
        detector_bank_group = self.add_detector(name, number)
        self.add_dataset(detector_bank_group, 'sensor_thickness', thickness, {'units': 'metres'})
        self.add_dataset(detector_bank_group, 'distance', distance, {'units': 'metres'})
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

    def add_shape(self, group, name, vertices, faces, detector_faces=None):
        """
        Add an NXshape to define geometry in OFF-like format

        :param group: Group to add the NXshape group to
        :param name: Name of the NXshape group
        :param vertices: 2D numpy array list of [x,y,z] coordinates of vertices
        :param faces: 2D numpy array list of vertex indices in each face, right-hand rule for face normal
        :param detector_faces: Optional 2D numpy array list of face number-detector id pairs
        :return: NXshape group
        """
        shape = nexusutils.add_nx_group(group, name, 'NXshape')
        shape.create_dataset('vertices', data=vertices)
        self.add_dataset(shape, 'faces', faces, {'vertices_per_face': 4})
        if detector_faces is not None:
            shape.create_dataset('detector_faces', data=detector_faces)
        return shape

    def add_tube_pixel(self, group, height, radius, centre=None, number_of_vertices=100):
        """
        Axis is assumed to be along x
        :param group: Group to add the pixel geometry to
        :param height: Height of the tube
        :param radius: Radius of the tube
        :param centre: On-axis centre at the end of the tube in form [x, y, z]
        :param number_of_vertices: Maximum number of vertices to use to describe pixel
        :return: NXshape describing a single pixel
        """
        if centre is None:
            centre = [0, 0, 0]
        angles = np.linspace(0, 2 * np.pi, np.floor((number_of_vertices / 2) + 1))
        # The last point is the same as the first so get rid of it
        angles = angles[:-1]
        y = centre[1] + radius * np.cos(angles)
        z = centre[2] + radius * np.sin(angles)
        num_points_at_each_tube_end = len(y)
        vertices = np.concatenate((
            np.array(list(zip(np.zeros(len(y)), y, z))),
            np.array(list(zip(np.ones(len(y)) * height, y, z)))))
        #
        # points around left circle tube-end       points around right circle tube-end
        #                                          (these follow the left ones in vertices list)
        #  circular boundary ^                     ^
        #                    |                     |
        #     nth_vertex + 2 .                     . nth_vertex + num_points_at_each_tube_end + 2
        #     nth_vertex + 1 .                     . nth_vertex + num_points_at_each_tube_end + 1
        #     nth_vertex     .                     . nth_vertex + num_points_at_each_tube_end
        #                    |                     |
        #  circular boundary v                     v
        #
        faces = [
            [nth_vertex, nth_vertex + num_points_at_each_tube_end, nth_vertex + num_points_at_each_tube_end + 1,
             nth_vertex + 1] for nth_vertex in range(num_points_at_each_tube_end - 1)]
        # Append the last rectangular face
        faces.append([num_points_at_each_tube_end - 1, (2 * num_points_at_each_tube_end) - 1,
                      num_points_at_each_tube_end, 0])
        # NB this is a tube, not a cylinder, I'm not adding the circular faces on the ends of the tube
        faces = np.array(faces)
        pixel_shape = self.add_shape(group, 'pixel_shape', vertices, faces)
        return pixel_shape

    def add_grid_pattern(self, detector_group, name, id_start, position_start, size, id_steps, steps):
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
        self.add_dataset(grid_pattern, 'position_start', position_start, {'units': 'metres'})
        grid_pattern.create_dataset('size', data=np.array([size]))
        grid_pattern.create_dataset('X_id_step', data=np.array([id_steps[0]]))
        grid_pattern.create_dataset('Y_id_step', data=np.array([id_steps[1]]))
        if len(id_steps) > 2:
            grid_pattern.create_dataset('Z_id_step', data=np.array([id_steps[2]]))
        self.add_dataset(grid_pattern, 'X_step', [steps[0]], {'units': 'metres'})
        self.add_dataset(grid_pattern, 'Y_step', [steps[1]], {'units': 'metres'})
        if len(steps) > 2:
            self.add_dataset(grid_pattern, 'Z_step', [steps[2]], {'units': 'metres'})
        return grid_pattern

    def __add_pixel_direction(self, detector_module, name, pixel_direction_offset, pixel_direction_step,
                              direction_size):
        if all(arg is not None for arg in [name, pixel_direction_offset, pixel_direction_step, direction_size]):
            if len(pixel_direction_offset) != 3:
                logger.error(
                    'In add_detector_module the pixel direction offset' +
                    ' must each have three values (corresponding to the cartesian axes)' +
                    ' Module name: ' + name)
            self.add_dataset(detector_module, name, 0, {'transformation_type': 'translation',
                                                        'offset_units': 'metres',
                                                        'offset': pixel_direction_offset,
                                                        'size_in_pixels': direction_size,
                                                        'pixel_number_step': pixel_direction_step})
        else:
            logger.debug('Missing arguments in __add_pixel_direction to define direction: ' + name)

    def __add_detector_bank_axis(self, group, axis, pixel_size, pixel_offset, beam_centre):
        self.add_dataset(group, axis + '_pixel_size', pixel_size, {'units': 'metres'})
        self.add_dataset(group, 'beam_center_' + axis, beam_centre, {'units': 'metres'})
        if pixel_offset is not None:
            self.add_dataset(group, axis + '_pixel_offset', pixel_offset, {'units': 'metres'})

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

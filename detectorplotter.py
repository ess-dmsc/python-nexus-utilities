import h5py
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import nexusutils


class DetectorPlotter:
    """
    Produce a simple scatter plot of detector pixel locations
    """

    def __init__(self, nexus_filename):
        self.source_file = h5py.File(nexus_filename, 'r')

    def plot_pixel_positions(self):
        instrument_group = self.source_file['/raw_data_1/instrument']
        detector_group_paths = []
        for name, dataset_or_group in instrument_group.items():
            if 'NX_class' in dataset_or_group.attrs:
                if str(dataset_or_group.attrs['NX_class'].astype(str)) == 'NXdetector':
                    detector_group_paths.append(dataset_or_group.name)
        fig, ax = plt.subplots(nrows=2, ncols=1)
        for detector_path in detector_group_paths:
            detector_group = self.source_file.get(detector_path)
            x_offsets = detector_group.get('x_pixel_offset')
            y_offsets = detector_group.get('y_pixel_offset')
            z_offsets = detector_group.get('z_pixel_offset')
            if z_offsets is None:
                z_offsets = np.zeros_like(x_offsets)
            x_offsets = x_offsets[:]
            y_offsets = y_offsets[:]
            z_offsets = z_offsets[:]

            depends_on = detector_group.get('depends_on')
            transformations = list()
            self.__get_transformations(depends_on, transformations)
            x_offsets, y_offsets, z_offsets = self.__do_transformations(transformations,
                                                                        x_offsets, y_offsets, z_offsets)

            ax[0].scatter(x_offsets, y_offsets, s=0.75, marker='x')
            ax[1].scatter(x_offsets, z_offsets, s=0.75, marker='x')

        ax[0].set_title('XY-plane pixel locations')
        ax[1].set_title('XZ-plane pixel locations')
        plt.axis('equal')
        plt.show()

    def __get_transformations(self, depends_on, transformations):
        """
        Get all transformations in the depends_on chain
        NB, these need to then be applied in reverse order

        :param depends_on: The first depends_on path string
        :param transformations: List of transformations to populate
        """
        if depends_on is not None:
            try:
                transform_path = str(depends_on[...].astype(str))
            except:
                transform_path = depends_on.decode()
            if transform_path != '.':
                transform = self.source_file.get(transform_path)
                next_depends_on = self.__get_transformation(transform, transformations)
                self.__get_transformations(next_depends_on, transformations)

    @staticmethod
    def __get_transformation(transform, transformations):
        attributes = transform.attrs
        if str(attributes['transformation_type'].astype(str)) == 'translation':
            vector = attributes['vector'] * transform[...].astype(float)
            vector = vector[0]
            transformations.append({'type': 'translation', 'matrix': vector})
        if str(attributes['transformation_type'].astype(str)) == 'rotation':
            axis = attributes['vector']
            angle = np.deg2rad(transform[...].astype(float))[0][0]
            rotation_matrix = nexusutils.rotation_matrix_from_axis_and_angle(axis, angle)
            transformations.append({'type': 'rotation', 'matrix': rotation_matrix})
        return attributes['depends_on']

    @staticmethod
    def __do_transformations(transformations, x_offsets, y_offsets, z_offsets):
        if len(x_offsets.shape) > 1:
            x_offsets = np.reshape(x_offsets, (1, np.prod(x_offsets.shape)))
            y_offsets = np.reshape(y_offsets, (1, np.prod(x_offsets.shape)))
            z_offsets = np.reshape(z_offsets, (1, np.prod(x_offsets.shape)))
        offsets = np.vstack((x_offsets, y_offsets, z_offsets))
        # Transformations must be carried out in reverse order
        for transformation in reversed(transformations):
            if transformation['type'] == 'translation':
                offsets += np.expand_dims(transformation['matrix'], 1)
            elif transformation['type'] == 'rotation':
                offsets = np.dot(transformation['matrix'], offsets)
            else:
                raise TypeError('Unrecognised transformation type in DetectorPlotter.__do_transformations')
        return offsets[0, :], offsets[1, :], offsets[2, :]

    def __del__(self):
        # Wrap in try to ignore exception which h5py likes to throw with Python 3.5
        try:
            self.source_file.close()
        except Exception:
            pass

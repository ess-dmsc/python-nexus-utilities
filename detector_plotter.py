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

    def plot_detectors(self):
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
            self.__do_transformations(depends_on, x_offsets, y_offsets, z_offsets)

            ax[0].scatter(x_offsets, y_offsets, s=0.5)
            ax[0].set_title('XY-plane pixel locations')
            ax[1].scatter(x_offsets, z_offsets, s=0.5)
            ax[1].set_title('XZ-plane pixel locations')
        plt.axis('equal')
        plt.show()

    def __do_transformations(self, depends_on, x_offsets, y_offsets, z_offsets):
        if depends_on is not None:
            try:
                transform_path = str(depends_on[...].astype(str))
            except:
                transform_path = depends_on.decode()
            if transform_path != '.':
                transform = self.source_file.get(transform_path)
                next_depends_on, x_offsets, y_offsets, z_offsets = self.__do_transformation(transform, x_offsets,
                                                                                            y_offsets, z_offsets)
                self.__do_transformations(next_depends_on, x_offsets, y_offsets, z_offsets)

    @staticmethod
    def __do_transformation(transform, x_offsets, y_offsets, z_offsets):
        attributes = transform.attrs
        if str(attributes['transformation_type'].astype(str)) == 'translation':
            vector = attributes['vector'] * transform[...].astype(float)
            vector = vector[0]
            x_offsets += vector[0]
            y_offsets += vector[1]
            z_offsets += vector[2]
        if str(attributes['transformation_type'].astype(str)) == 'rotation':
            axis = attributes['vector'] * transform[...].astype(float)
            angle = transform[...].astype(float)
            rotation_matrix = nexusutils.rotation_matrix_from_axis_and_angle(axis, angle)
            offsets = np.hstack((x_offsets, y_offsets, z_offsets))
            offsets = rotation_matrix.dot(offsets.T)
            x_offsets = offsets[:, 1]
            y_offsets = offsets[:, 2]
            z_offsets = offsets[:, 3]
        return attributes['depends_on'], x_offsets, y_offsets, z_offsets

    def __del__(self):
        # Wrap in try to ignore exception which h5py likes to throw with Python 3.5
        try:
            self.source_file.close()
        except Exception:
            pass


if __name__ == '__main__':
    # plotter = DetectorPlotter('example_instruments/sans2d/SANS_example_gzip_compress.hdf5')
    plotter = DetectorPlotter('example_instruments/wish/WISH_example_gzip_compress.hdf5')
    plotter.plot_detectors()

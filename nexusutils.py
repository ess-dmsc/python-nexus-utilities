import numpy as np
import h5py


def is_scalar(object_to_check):
    if hasattr(object_to_check, "__len__"):
        return len(object_to_check) == 1
    return True


def wipe_file(filename):
    with h5py.File(filename, 'w') as f_write:
        pass


def add_nx_group(parent_group, group_name, nx_class_name):
    created_group = parent_group.create_group(group_name)
    created_group.attrs.create('NX_class', np.array(nx_class_name).astype('|S' + str(len(nx_class_name))))
    return created_group


def normalise(input_vector):
    """
    Normalise to unit vector

    :param input_vector: Input vector (numpy array)
    :param axis: The axis along which to normalise
    :param order: Order of the norm, see https://docs.scipy.org/doc/numpy/reference/generated/numpy.linalg.norm.html
    :return: Unit vector, magnitude
    """
    magnitude = np.sqrt(np.sum(np.square(input_vector)))
    unit_vector = input_vector/magnitude
    return unit_vector, magnitude

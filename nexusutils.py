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


def add_translation(group, transformation_info):
    # TODO finish (add datasets)
    add_nx_group(group, 'transformation', 'NXtransformation')

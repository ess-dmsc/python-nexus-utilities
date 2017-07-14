import numpy as np
import h5py
from nxlogexample import create_nexus_file


if __name__ == '__main__':
    # Make an example file with an NXlog and some neutron event data in it
    filename = 'SANS2D_NXlog_example.hdf5'
    create_nexus_file(filename)

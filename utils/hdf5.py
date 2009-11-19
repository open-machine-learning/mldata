"""
HDF5-specific utils for mldata
"""

import os, h5py, numpy
from settings import MEDIA_ROOT



def convert(filename, format='csv'):
    if format != 'csv':
        return False

    filename_orig = MEDIA_ROOT + filename
    orig = open(filename_orig, 'r')
    labels = []
    for line in orig:
        labels.append(numpy.double(line.split(' ')[0]))
    orig.close()

    filename_hdf5 = MEDIA_ROOT + filename.split('.')[0] + '.hdf5'
    hdf5 = h5py.File(filename_hdf5, 'w')
    hdf5.create_dataset('labels', data=numpy.array(labels))
    hdf5.attrs['mldata'] = 0
    hdf5.attrs['task'] = 'classification'
    hdf5.close()
    os.remove(filename_orig)

    return True

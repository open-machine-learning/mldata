from hdf5 import *


def convert(in_filename, in_format, out_filename, out_format):
    conv = None
    if in_format == 'libsvm' and out_format == 'hdf5':
        conv = LibSVM2HDF5(in_filename, out_filename)
    elif in_format == 'arff' and out_format == 'hdf5':
        conv = ARFF2HDF5(in_filename, out_filename)
    elif in_format == 'hdf5' and out_format == 'arff':
        conv = HDF52ARFF(in_filename, out_filename)

    if conv:
        print 'Converting from %s to %s...' % (in_format, out_format)
        res = conv.run()
        if res:
            print 'Success!'
        else:
            print 'Fail!'
        return res
    else:
        print 'Unknown conversion pair %s to %s!' % (in_format, out_format)
        return False




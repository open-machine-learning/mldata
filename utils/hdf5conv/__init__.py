from hdf5 import *


def convert(in_filename, in_format, out_filename, out_format):
    """Convert the given file in given format to given file in given format."""
    conv = None
    if in_format == 'libsvm' and out_format == 'hdf5':
        conv = LibSVM2HDF5(in_filename, out_filename)
    elif in_format == 'arff' and out_format == 'hdf5':
        conv = ARFF2HDF5(in_filename, out_filename)
    elif in_format == 'hdf5' and out_format == 'arff':
        conv = HDF52ARFF(in_filename, out_filename)

    if conv:
        #print 'Converting from %s to %s...' % (in_format, out_format)
        return conv.run()
    else:
        #print 'Unknown conversion pair %s to %s!' % (in_format, out_format)
        return False


def get_filename(orig):
    return orig + '.hdf5'


def get_unparseable(filename):
    file = open(filename, 'r')
    i = 0
    data = []
    for line in file:
        data.append(line)
        i += 1
        if i > 23:
            break
    data = "\n".join(data)

    return {'attributes': 'unparseable data:' + data}


def get_extract(in_filename):
    in_format = in_filename.split('.')[-1]
    out_filename = get_filename(in_filename)

    if in_format != 'hdf5':
        if not convert(in_filename, in_format, out_filename, 'hdf5'):
            return get_unparseable(in_filename)
        filename = out_filename
    else:
        filename = in_filename

    return hdf5_extract(filename)

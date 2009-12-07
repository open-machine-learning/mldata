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


def is_binary(filename):
    """Return true if the given filename is binary."""
    f = open(filename, 'rb')
    try:
        CHUNKSIZE = 1024
        while 1:
            chunk = f.read(CHUNKSIZE)
            if '\0' in chunk: # found null byte
                f.close()
                return 1
            if len(chunk) < CHUNKSIZE:
                break # done
    finally:
        f.close()

    return 0


def get_filename(orig):
    return orig + '.hdf5'


def get_fileformat(filename):
    """Determine fileformat by given filenname."""
    suffix = filename.split('.')[-1]
    if suffix == 'txt':
        return 'libsvm'
    elif suffix == 'arff':
        return suffix
    elif suffix == 'hdf5':
        return suffix
    elif suffix in ('bz2', 'gz'):
        presuffix = filename.split('.')[-2]
        if presuffix == 'tar':
            return presuffix + '.' + suffix
        return suffix
    else: # unknown
        return suffix


def get_unparseable(filename, format):
    import tarfile, zipfile
    if zipfile.is_zipfile(filename):
        intro = 'ZIP archive'
        f = zipfile.ZipFile(filename)
        data = ', '.join(f.namelist())
        f.close()
    elif tarfile.is_tarfile(filename):
        intro = '(Zipped) TAR archive'
        f = tarfile.TarFile.open(filename)
        data = ', '.join(f.getnames())
        f.close()
    else:
        intro = 'Unparseable Data'
        if is_binary(filename):
            data = ''
        else:
            file = open(filename, 'r')
            i = 0
            data = []
            for line in file:
                data.append(line)
                i += 1
                if i > NUM_EXTRACT:
                    break
            data = "\n".join(data)

    return {'attributes': [[intro, data]]}


def get_extract(in_filename):
    in_format = get_fileformat(in_filename)
    out_filename = get_filename(in_filename)

    if in_format != 'hdf5':
        if not convert(in_filename, in_format, out_filename, 'hdf5'):
            return get_unparseable(in_filename, in_format)
        filename = out_filename
    else:
        filename = in_filename

    return hdf5_extract(filename)

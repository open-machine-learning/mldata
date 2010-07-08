import base, h5py

def infer_seperator(fname):
    """Infer seperator for variables in given file.

    @param fname: filename to retrieve data from
    @type fname: string
    @return: inferred seperator
    @rtype: string
    """
    fp = open(fname, 'r')
    seperator = None
    minimum = 1

    for line in fp:
        for s in base.ALLOWED_SEPERATORS:
            l = len(line.split(s))
            if l > minimum:
                minimum = l
                seperator = s
        if seperator:
            break

    fp.close()
    if not seperator:
        return ''
    else:
        return seperator


def _try_suffix(fname):
    """Get format of given file by suffix.

    @param fname: name of file to determine format for
    @type fname: string
    """
    suffix = fname.split('.')[-1]
    # just assume libsvm if no proper suffix
    if suffix.find('/') != -1:
        return '', False

    if suffix in ('svm', 'libsvm'):
        return 'libsvm', True
    elif suffix in ('arff'):
        return 'arff', True
    elif suffix in ('h5', 'hdf5'):
        return 'h5', True
    elif suffix in ('csv', 'tsv'):
        return 'csv', True
    elif suffix in ('uci', 'data'):
        return 'uci', True
    elif suffix in ('bz2', 'gz', 'zip'):
        try:
            presuffix = fname.split('.')[-2]
            if presuffix == 'tar':
                return presuffix + '.' + suffix, True
        except IndexError:
            pass
        return suffix, True
    elif suffix in ('mat', 'm', 'matlab'):
        return 'matlab', True
    elif suffix in ('octave', 'oct'):
        return 'octave', True
    else: # unknown
        return suffix, False


def _try_arff(fname):
    """Try if given file is in arff format

    @param fname: name of file to determine format for
    @type fname: string
    """
    try:
        import arff
        arff.ArffFile.load(fname)
        return True
    except:
        return False


def _try_csv(fname):
    """Try if given file is in csv format

    @param fname: name of file to determine format for
    @type fname: string
    """
    if infer_seperator(fname) == ',':
        return True
    else:
        return False


def _try_libsvm(fname):
    """Try if given file is in libsvm format

    @param fname: name of file to determine format for
    @type fname: string
    """
    try:
        fp = open(fname, 'r')
    except:
        return False

    line = fp.readline()
    attributes = line.split()
    if len(attributes) > 1:
        # 0th might be label, so look at 1st
        if len(attributes[1].split(':')) == 2:
            fp.close()
            return True

    fp.close()
    return False


def _try_h5(fname):
    """Try if given file is in hdf5 format

    @param fname: name of file to determine format for
    @type fname: string
    """
    try:
        fp = h5py.File(fname, 'r')
    except:
        return False

    fp.close()
    return True



def get(fname, skip_suffix=False):
    """Get format of given file.

    By suffix it detects: libsvm, arff, csv, h5, uci, tar.gz, tar.bz2, zip,
    matlab, octave.
    By deeper inspection it detects: arff, csv, libsvm, h5.

    @param fname: name of file to determine format for
    @type fname: string
    @param skip_suffix: if detection by suffix (first priority) shall be skipped
    @type skip_suffix: boolean
    """
    if not skip_suffix:
        format, found = _try_suffix(fname)
        if found:
            return format

    if _try_arff(fname): return 'arff'
    elif _try_csv(fname): return 'csv'
    elif _try_libsvm(fname): return 'libsvm'
    elif _try_h5(fname): return 'h5'

    return 'unknown'

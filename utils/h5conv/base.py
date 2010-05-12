import os, numpy, h5py
from gettext import gettext as _
from scipy.sparse import csc_matrix

VERSION = '0.3'
VERSION_MLDATA = '0'
NUM_EXTRACT = 10
COMPRESSION = None
ALLOWED_SEPERATORS = [',', ' ', "\t"]


class H5Converter(object):
    """Base converter class.

    @cvar str_type: string type to be used for variable length strings in h5py
    @type str_type: numpy.dtype

    @ivar fname_in: filename to read data from
    @type fname_in: string
    @ivar fname_out: filename to write converted data to
    @type fname_out: string
    @ivar labels_idx: indices for labels for each row
    @type labels_idx: list of integers
    @ivar seperator: seperator to seperate variables in examples
    @type seperator: string
    """
    str_type = h5py.new_vlen(numpy.str)


    def __init__(self, fname_in, fname_out, seperator=','):
        self.fname_in = fname_in
        self.fname_out = fname_out
        self.labels_idx = None
        self.seperator = seperator


    def set_seperator(self, seperator):
        """Set the seperator to seperate variables in examples.

        @param seperator: seperator to use
        @type seperator: string
        """
        if seperator in ALLOWED_SEPERATORS:
            self.seperator = seperator
        else:
            raise AttributeError(_('Seperator %s not allowed!' % seperator))


    def warn(self, msg):
        """Print a warning message.

        @param msg: message to print
        @type msg: string
        """
        return
        print 'WARNING: ' + msg


    def get_name(self):
        """Get dataset name from given file.

        @return: comment
        @rtype: string
        """
        # without str() it might barf
        return str(os.path.basename(self.fname_in).split('.')[0])


    def get_comment(self):
        """Get comment from given file.

        @return: comment
        @rtype: string
        """
        raise NotImplementedError('Abstract method!')


    def get_types(self):
        """Get attribute/data types, if available.

        @return: array of attribute/data types
        @rtype: numpy array
        """
        return numpy.array([])


    def get_data(self):
        """Get data from given file.

        @return: data names, ordering and examples
        @rtype: dict of: list of names, list of ordering and dict of examples
        """
        raise NotImplementedError('Abstract method!')


    def _get_merged(self, data):
        """Merge given data where appropriate.

        String arrays are not merged, but all int and all double are merged
        into one matrix.

        @param data: data structure as returned by get_data()
        @type data: dict
        @return: merged data structure
        @rtype: dict
        """
        # nothing to do if we have one sparse matrix
        if 'data' and 'indices' and 'indptr' in data['ordering']:
            return data

        merged = {}
        for name in data['ordering']:
            val = data['data'][name]
            if len(val) < 1:
                continue

            t = type(val[0])
            if t == numpy.int32:
                path = 'int'
            elif t == numpy.double:
                path = 'double'
            else: # string
                if name.find('/') != -1: # / sep belongs to hdf5 path
                    path = name.replace('/', '+')
                    data['ordering'][data['ordering'].index(name)] = path
                else:
                    path = name
                merged[path] = val
                continue

            if not path in merged:
                merged[path] = []
            merged[path].append(val)

        data['data'] = merged
        return data


    def run(self):
        """Run the actual conversion process."""
        h5file = h5py.File(self.fname_out, 'w')

        h5file.attrs['name'] = self.get_name()
        h5file.attrs['mldata'] = VERSION_MLDATA
        h5file.attrs['comment'] = self.get_comment()

        data = self._get_merged(self.get_data())
        group = h5file.create_group('/data')
        for path, val in data['data'].iteritems():
            group.create_dataset(path, data=val, compression=COMPRESSION)
        if 'label' in data and data['label'].size > 0:
            group.create_dataset('/data/label', data=data['label'], compression=COMPRESSION)

        group = h5file.create_group('/data_descr')
        names = numpy.array(data['names']).astype(self.str_type)
        if names.size > 0: # simple 'if names' throws exception if array
            group.create_dataset('names', data=names, compression=COMPRESSION)
        ordering = numpy.array(data['ordering']).astype(self.str_type)
        if ordering.size > 0:
            group.create_dataset('ordering', data=ordering, compression=COMPRESSION)
        types = self.get_types()
        if types.size > 0:
            types = types.astype(self.str_type)
            group.create_dataset('types', data=types, compression=COMPRESSION)

        h5file.close()

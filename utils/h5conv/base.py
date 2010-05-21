import os, numpy, h5py
from gettext import gettext as _
from scipy.sparse import csc_matrix

VERSION = '0.3'
VERSION_MLDATA = '0'
NUM_EXTRACT = 10
COMPRESSION = None
# white space seperator(s) is implicit
ALLOWED_SEPERATORS = (',')

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


    def __init__(self, fname_in, fname_out, seperator=None):
        self.fname_in = fname_in
        self.fname_out = fname_out
        self.labels_idx = None
        self.set_seperator(seperator)

        # sometimes it seems files are not properly overwritten when opened by
        # 'w' during run().
        if os.path.exists(fname_out):
            os.remove(fname_out)


    def set_seperator(self, seperator):
        """Set the seperator to seperate variables in examples.

        @param seperator: seperator to use
        @type seperator: string
        """
        if not seperator:
            self.seperator = None
            return

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

############### from HDF5 #######################

    def get_outdata(self, h5):
        """Get data structure ready to be written to file.

        @param h5: HDF5 file
        @type h5: File object
        @return: blob of data
        @rtype: list of lists
        """
        if 'indices' in h5['/data']:
            return self._get_sparse(h5)
        elif 'label' in h5['/data']: # only labels + data
            return self._get_label_data(h5)
        else:
            return self._get_multiple_sets(h5)


    def _get_sparse(self, h5):
        """Sparse data structure.

        @param h5: HDF5 file
        @type h5: File object
        @return: blob of data
        @rtype: list of lists
        """
        labels = h5['/data/label'][:]
        A = csc_matrix((h5['/data/data'], h5['/data/indices'], h5['/data/indptr'])).todense().T
        data = []

        for i in xrange(A.shape[0]):
            line = [str(labels[i][0])]
            for j in xrange(A.shape[1]):
                line.append(str(A[i, j]))
            data.append(line)

        return data



    def _get_label_data(self, h5):
        """Get 'simple' label + data structure.

        @param h5: HDF5 file
        @type h5: File object
        @return: blob of data
        @rtype: list of lists
        """
        data = []
        A = numpy.matrix(h5['/data/data']).T
        labels = h5['/data/label'][:]
        num_lab = len(labels)

        if len(labels[0]) == 1:
            label_vector = True
        else:
            label_vector = False

        # prepend labels
        for i in xrange(A.shape[0]):
            line = []
            if label_vector:
                line.append(str(labels[i][0]))
            else:
                for j in xrange(num_lab):
                    line.append(str(labels[j][i]))
            for j in xrange(A.shape[1]):
                line.append(str(A[i, j]))
            data.append(line)

        return data


    def _get_multiple_sets(self, h5):
        """Get 'complex' data structure.

        @param h5: HDF5 file
        @type h5: File object
        @return: blob of data
        @rtype: list of lists
        """
        # when using faster [:] instead of slower list(), str() would have to
        # be used later on
        names = list(h5['/data_descr/ordering'])
        data = []

        if '/data/int' in h5:
            len_int = len(h5['/data/int'])
        else:
            len_int = 0
        idx_int = 0

        if '/data/double' in h5:
            len_double = len(h5['/data/double'])
        else:
            len_double = 0
        idx_double = 0

        for name in names:
            if name in h5['/data']:
                data.append(h5['/data/' + name][:])
            elif name.startswith('int'):
                data.append(h5['/data/int'][idx_int])
                idx_int += 1
            elif name.startswith('double'):
                data.append(h5['/data/double'][idx_double])
                idx_double += 1
            else: # either int or double
                if len_int and idx_int < len_int and type(h5['/data/int'][idx_int][0]) == numpy.int32:
                    data.append(h5['/data/int'][idx_int])
                    idx_int += 1
                elif len_double and idx_double < len_double and type(h5['/data/double'][idx_double][0]) == numpy.double:
                    data.append(h5['/data/double'][idx_double])
                    idx_double += 1
                else:
                    raise AttributeError('Dunno how to handle dataset ' + name)

        # A = numpy.matrix(data).T.astype(str) triggers memory corruption
        if len(data) == 1:
            A = numpy.matrix(data[0]).T # only one data blob
        else:
            A = numpy.matrix(data).T

        data = []
        for i in xrange(A.shape[0]):
            line = map(str, A[i].tolist()[0])
            data.append(line)

        return data


############### to HDF5 #######################

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
        return ''


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


    def get_datatype(self, values):
        """Get data type of given values.

        @param values: list of values to check
        @type values: list
        @return: data type to use for conversion
        @rtype: numpy.int32/numpy.double/self.str_type
        """
        dtype = None

        for v in values:
            if isinstance(v, int):
                dtype = numpy.int32
            elif isinstance(v, float):
                dtype = numpy.double
            else: # maybe int/double in string
                try:
                    tmp = int(v)
                    dtype = numpy.int32
                except ValueError:
                    try:
                        tmp = float(v)
                        dtype = numpy.double
                    except ValueError:
                        return self.str_type

        return dtype


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
        try:
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
        except ValueError, e:
            h5file.close()
            os.remove(self.fname_out)
            raise ValueError(e)
        else:
            h5file.close()

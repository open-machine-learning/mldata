import os, numpy, h5py
from gettext import gettext as _
from scipy.sparse import csc_matrix


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


    def __init__(self, fname_in, fname_out, seperator=None, remove_out=True):
        """
        @param seperator: seperator used to seperate examples
        @type seperator: string
        @param remove_out: if output file shall be removed before running.
        @type remove_out: boolean
        """
        self.fname_in = fname_in
        self.fname_out = fname_out
        self.labels_idx = None
        self.set_seperator(seperator)

        # sometimes it seems files are not properly overwritten when opened by
        # 'w' during run().
        if remove_out and os.path.exists(fname_out):
            os.remove(fname_out)


    def run(self):
        """Run the actual conversion process."""
        raise NotImplementedError('Abstract method!')


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



    def _get_complex_data(self, h5):
        """Get 'complex' data structure.

        @param h5: HDF5 file
        @type h5: File object
        @return: blob of data
        @rtype: list of lists
        """
        # de-merge
        data = []
        for name in h5['/data_descr/ordering']:
            block = h5['/data/' + name][:]
            if type(block[0])== numpy.ndarray:
                for i in xrange(len(block)):
                    data.append(block[i])
            else:
                data.append(block)

        return numpy.matrix(data).T.tolist()


    def get_name(self):
        """Get dataset name from non-HDF5 file

        @return: comment
        @rtype: string
        """
        # without str() it might barf
        return str(os.path.basename(self.fname_in).split('.')[0])


    def get_comment(self):
        """Get comment from non-HDF5 file.

        @return: comment
        @rtype: string
        """
        return ''


    def get_types(self):
        """Get attribute/data types, if available, from non-HDF5 file

        @return: array of attribute/data types
        @rtype: numpy array
        """
        return numpy.array([])


    def get_contents(self):
        """Get in-memory data, labels and data description

        If not overwritten by child class, it will retrieve data from the HDF
        input file.

        @return: data names, ordering, labels and the examples
        @rtype: dict of: list of names, list of ordering and dict of examples
        """
        h5 = h5py.File(self.fname_in, 'r')
        contents = {
            'names': h5['/data_descr/names'][:],
            'ordering': h5['/data_descr/ordering'][:]
        }

        if 'indices' in h5['/data']:
            contents['data'] = csc_matrix(
                (h5['/data/data'], h5['/data/indices'], h5['/data/indptr'])
            ).todense().tolist()
            contents['label'] = numpy.matrix(h5['/data/label']).tolist()
        elif 'label' in h5['/data']:
            contents['data'] = numpy.matrix(h5['/data/data']).T.tolist()
            contents['label'] = numpy.matrix(h5['/data/label']).tolist()
        else:
            contents['data'] = self._get_complex_data(h5)

        h5.close()
        return contents


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
                    if not dtype: # a previous nan might set it to double
                        dtype = numpy.int32
                except ValueError:
                    try:
                        tmp = float(v)
                        dtype = numpy.double
                    except ValueError:
                        return self.str_type

        return dtype


    def _get_merged(self, contents):
        """Merge given data where appropriate.

        String arrays are not merged, but all int and all double are merged
        into one matrix.

        @param contents: data structure as returned by get_contents()
        @type contents: dict
        @return: merged data structure
        @rtype: dict
        """
        # nothing to do if we have one sparse matrix
        if 'data' and 'indices' and 'indptr' in contents['ordering']:
            return contents

        merged = {}
        ordering = []
        path = ''
        idx_int = 0
        idx_double = 0
        merging = None
        for name in contents['ordering']:
            if name == 'label': continue

            val = contents['data'][name]
            if len(val) < 1: continue

            t = type(val[0])
            if t == numpy.int32:
                if merging == 'int':
                    merged[path].append(val)
                else:
                    merging = 'int'
                    path = 'int' + str(idx_int)
                    ordering.append(path)
                    merged[path] = [val]
                    idx_int += 1
            elif t == numpy.double:
                if merging == 'double':
                    merged[path].append(val)
                else:
                    merging = 'double'
                    path = 'double' + str(idx_double)
                    ordering.append(path)
                    merged[path] = [val]
                    idx_double += 1
            else: # string or matrix
                merging = None
                if name.find('/') != -1: # / sep belongs to hdf5 path
                    path = name.replace('/', '+')
                    contents['ordering'][contents['ordering'].index(name)] = path
                else:
                    path = name
                ordering.append(path)
                merged[path] = val

        contents['data'] = merged
        contents['ordering'] = ordering
        return contents


    def run(self):
        """Convert from input file to HDF5 file."""
        h5 = h5py.File(self.fname_out, 'w')

        h5.attrs['name'] = self.get_name()
        h5.attrs['mldata'] = VERSION_MLDATA
        h5.attrs['comment'] = self.get_comment()

        try:
            contents = self._get_merged(self.get_contents())

            group = h5.create_group('/data')
            for path, val in contents['data'].iteritems():
                group.create_dataset(path, data=val, compression=COMPRESSION)
            if 'label' in contents:
                group.create_dataset('/data/label', data=contents['label'], compression=COMPRESSION)

            group = h5.create_group('/data_descr')
            names = numpy.array(contents['names']).astype(self.str_type)
            if names.size > 0: # simple 'if names' throws exception if array
                group.create_dataset('names', data=names, compression=COMPRESSION)
            ordering = numpy.array(contents['ordering']).astype(self.str_type)
            if ordering.size > 0:
                group.create_dataset('ordering', data=ordering, compression=COMPRESSION)
            types = self.get_types()
            if types.size > 0:
                types = types.astype(self.str_type)
                group.create_dataset('types', data=types, compression=COMPRESSION)
        except: # just do some clean-up
            h5.close()
            os.remove(self.fname_out)
            raise
        else:
            h5.close()


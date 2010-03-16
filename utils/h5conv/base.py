import os, numpy, h5py

VERSION = '0.3'
VERSION_MLDATA = '0'
NUM_EXTRACT = 10
COMPRESSION = None


class H5Converter(object):
    """Base converter class.

    @cvar str_type: string type to be used for variable length strings in h5py
    @type str_type: numpy.dtype

    @ivar fname_in: filename to read data from
    @type fname_in: string
    @ivar fname_out: filename to write converted data to
    @type fname_out: string
    """

    str_type = h5py.new_vlen(numpy.str)


    def __init__(self, fname_in, fname_out):
        self.fname_in = fname_in
        self.fname_out = fname_out


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
        """Get attribute/data types, if available."""
        return None


    def get_data(self):
        """Get data from given file.

        @return: data names, order and attributes
        @rtype: dict of: list of data names, list of data order and dict of data points
        """
        raise NotImplementedError('Abstract method!')


    def run(self):
        """Run the actual conversion process."""
        h5file = h5py.File(self.fname_out, 'w')

        h5file.attrs['name'] = self.get_name()
        h5file.attrs['mldata'] = VERSION_MLDATA
        h5file.attrs['comment'] = self.get_comment()

        data = self.get_data()
        names = numpy.array(data['names']).astype(self.str_type)
        h5file.create_dataset('names', data=names, compression=COMPRESSION)
        order = numpy.array(data['order']).astype(self.str_type)
        h5file.create_dataset('order', data=order, compression=COMPRESSION)

        types = self.get_types()
        if types:
            types = numpy.array(types).astype(self.str_type)
            h5file.create_dataset('types', data=types, compression=COMPRESSION)

        group = h5file.create_group('/data')
        for name in data['order']:
            group.create_dataset(name, data=data['data'][name], compression=COMPRESSION)

        h5file.close()

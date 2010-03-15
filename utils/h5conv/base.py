import os, numpy, h5py

VERSION = '0.3'
VERSION_MLDATA = '0'
NUM_EXTRACT = 10
COMPRESSION = None


class Converter():
    """Base converter class.

    @cvar str_type: string type to be used for variable length strings in h5py
    @type str_type: numpy.dtype
    """

    str_type = h5py.new_vlen(numpy.str)


    def warn(self, msg):
        """Print a warning message.

        @param msg: message to print
        @type msg: string
        """
        return
        print 'WARNING: ' + msg


    def get_comment(self, fname):
        """Get comment from given file.

        @param fname: filename to retrieve comment from
        @type fname: string
        @return: comment
        @rtype: string
        """
        raise NotImplementedError('Abstract method!')


    def get_data(self, name):
        """Get data from given file.

        @param fname: filename to get data from
        @type fname: string
        @return: data names, order and attributes
        @rtype: dict of: list of data names, list of data order and dict of data points
        """
        raise NotImplementedError('Abstract method!')


    def run(self, in_fname, out_fname):
        """Run the actual conversion process.

        @param in_fname: filename to read data from
        @type in_fname: string
        @param out_fname: filename to write converted data to
        @type out_fname: string
        """
        h5file = h5py.File(out_fname, 'w')

        # without str() it might barf
        h5file.attrs['name'] = str(os.path.basename(out_fname).split('.')[0])
        h5file.attrs['mldata'] = VERSION_MLDATA
        try:
            h5file.attrs['comment'] = self.get_comment(in_fname)
        except ValueError:
            h5file.attrs['comment'] = ''

        group = h5file.create_group('/data')
        data = self.get_data(in_fname)
        if data:
            names = numpy.array(data['names']).astype(self.str_type)
            group.create_dataset('names', data=names, compression=COMPRESSION)
            order = numpy.array(data['order']).astype(self.str_type)
            group.create_dataset('order', data=order, compression=COMPRESSION)
            for name in data['order']:
                group.create_dataset(name, data=data['data'][name], compression=COMPRESSION)

        h5file.close()

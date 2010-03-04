import h5py, os, numpy
import config

class UCI2H5():
    """Convert a file from UCI to HDF5."""

    def _get_comment(self, fname):
        """Get comment from given file.

        @param fname: filename to retrieve comment from
        @type fname: string
        @return: comment
        @rtype: string
        """
        name = '.'.join(fname.split('.')[:-1])
        if not name:
            name = '.'.join(fname.split('-')[:-1])

        if os.path.exists(name + '.names'):
            f = open(name + '.names', 'r')
        elif os.path.exists(name + '.info'):
            f = open(name + '.info', 'r')
        else:
            return None

        comment = ''.join(f.readlines())
        f.close()
        return comment


    def _get_dtype(self, line):
        dtype = []
        str_type = h5py.new_vlen(numpy.str)
        for item in line:
            try:
                numpy.int(item)
                dtype.append(('', numpy.int))
            except ValueError:
                try:
                    numpy.double(item)
                    dtype.append(('', numpy.double))
                except ValueError:
                    dtype.append(('', str_type))
        return numpy.dtype(dtype)


    def _get_data(self, fname):
        """Get data from given file.

        @param fname: filename to get data from
        @type fname: string
        @return: list of data attributes
        @rtype: tuple of (list of tuples of data) and their types
        """
        f = open(fname, 'r')
        data = []
        dtype = None
        for line in f:
            l = []
            for item in line.strip().split(','):
                if item:
                    l.append(item.strip())
            if l:
                if not dtype:
                    dtype = self._get_dtype(l)
                data.append(tuple(l)) # conv to tuple for h5py
        f.close()
        return (data, dtype)


    def run(self, in_fname, out_fname):
        """Run the actual conversion process.

        @param in_fname: filename to read data from
        @type in_fname: string
        @param out_fname: filename to write converted data to
        @type out_fname: string
        """
        h = h5py.File(out_fname, 'w')

        data, dtype = self._get_data(in_fname)
        if data:
            # doesn't work directly 'no appropriate function for conversion path'
            #h.create_dataset('attributes', data=data, dtype=dtype, compression=config.COMPRESSION)
            shape = (len(data),)
            ds = h.create_dataset('attributes', shape, dtype=dtype, compression=config.COMPRESSION)
            ds[...] = data

        # without str(), h5py might barf
        h.attrs['name'] = str(os.path.basename(out_fname).split('.')[0])
        h.attrs['mldata'] = config.VERSION_MLDATA
        h.attrs['comment'] = self._get_comment(in_fname)

        h.close()

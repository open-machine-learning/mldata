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


    def _get_dtype(self, fp):
        """This seems a bit mad, Ted."""
        str_type = h5py.new_vlen(numpy.str)
        num_items = len(fp.readline().strip().split(','))
        fp.seek(0)
        dtype = []

        for l in fp:
            line = l.strip().split(',')
            for i in xrange(num_items):
                item = line[i].strip()
                if item == '?':
                    continue

                try:
                    numpy.int(item)
                    dtype.insert(i, ('', numpy.int))
                except ValueError:
                    try:
                        numpy.double(item)
                        dtype.insert(i, ('', numpy.double))
                    except ValueError:
                        dtype.insert(i, ('', str_type))

                if len(dtype) == num_items:
                    fp.seek(0)
                    return numpy.dtype(dtype)



    def _get_data(self, fname):
        """Get data from given file.

        @param fname: filename to get data from
        @type fname: string
        @return: list of data attributes
        @rtype: tuple of (list of tuples of data) and their types
        """
        fp = open(fname, 'r')
        data = []
        dtype = self._get_dtype(fp)
        for line in fp:
            l = []
            for item in line.strip().split(','):
                if item:
                    if item == '?': # missing value
                        dt = dtype[len(l)]
                        # converting nan to the appropriate dtype
                        l.append(numpy.array([numpy.nan]).astype(dt)[0])
                    else:
                        try:
                            item = numpy.int(item)
                        except ValueError:
                            try:
                                item = numpy.double(item)
                            except ValueError:
                                item = item.strip()
                        l.append(item)
            if l:
                data.append(tuple(l)) # tuple required to please numpy
        fp.close()
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

        # without str() it might barf
        h.attrs['name'] = str(os.path.basename(out_fname).split('.')[0])
        h.attrs['mldata'] = config.VERSION_MLDATA
        h.attrs['comment'] = self._get_comment(in_fname)

        h.close()

import h5py, numpy
import arff, base



class ARFF2H5(base.H5Converter):
    """Convert a file from ARFF to HDF5 (spec of mldata.org).

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/

    @ivar arff: data from arff file
    @type arff: arff object
    """

    def __init__(self, *args, **kwargs):
        super(ARFF2H5, self).__init__(*args, **kwargs)
        self.arff = arff.ArffFile.load(self.fname_in)


    def get_name(self):
        return self.arff.relation


    def get_comment(self):
        return self.arff.comment


    def get_types(self):
        # need to get it in the right order
        types = []
        for name in self.arff.attributes:
            t = self.arff.attribute_types[name]
            if self.arff.attribute_data[name]:
                t += ':' + ','.join(self.arff.attribute_data[name])
            types.append(t)
        return numpy.array(types)


    def _rm_ticks(self, item):
        """Remove ticks from item if it is a string.

        Some attributes are surrounded by unnecessary ticks.

        @param item: item to check for ticks
        @type item: any, preferably str
        @return: unmodified item or item with ticks removed
        @rtype: type(item)
        """
        try:
            # a few attributes are designated strings by "'"
            if item[0] == "'" and item[-1] == "'":
                return item[1:-1]

        except TypeError:
            pass

        return item


    def _get_type(self, values):
        """Get data type of given values.

        @param values: list of values to check
        @type values: list
        @return: data type to use for conversion
        @rtype: numpy.int32/numpy.double/self.str_type
        """
        is_int = False
        is_double = False
        is_str = False

        for v in values:
            try:
                if int(v) == v:
                    is_int = True
                else:
                    is_int = False
                    is_double = True
            except ValueError:
                is_int = False
                is_double = False
                is_str = True
                break

        if is_int:
            return numpy.int32
        elif is_double:
            return numpy.double
        else:
            return self.str_type


    def get_data(self):
        data = {}
        names = []
        ordering = []

        for name in self.arff.attributes:
            n = self._rm_ticks(name)
            names.append(n)
            data[n] = []

        for item in self.arff.data:
            for i in xrange(len(data)):
                d = self._rm_ticks(item[i])
                data[names[i]].append(d)

        # conversion to proper data types
        for name, values in data.iteritems():
            t = self._get_type(values)
            data[name] = numpy.array(values).astype(t)

        return {'names':names, 'ordering':names, 'data':data}



class H52ARFF(base.H5Converter):
    """Convert a file from HDF5 (spec of mldata.org) to ARFF

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/
    """


    def run(self):
        """Run the actual conversion process.

        @param in_fname: filename to read data from
        @type in_fname: string
        @param out_fname: filename to write converted data to
        @type out_fname: string
        """
        a = arff.ArffFile()
        h5 = h5py.File(self.fname_in, 'r')

        names = h5['/data_descr/names'][:]
        a.relation = h5.attrs['name']
        a.comment = h5.attrs['comment']
        a.attributes = names
        a.data = self.get_outdata(h5)

        # handle arff types
        if '/data_descr/types' in h5:
            types = h5['/data_descr/types'][:]
        else:
            types = []
            for n in names:
                if n.startswith('int') or n.startswith('double'):
                    types.append('numeric')
                else:
                    types.append('string')

        for i in xrange(len(types)):
            t = types[i].split(':')
            a.attribute_types[a.attributes[i]] = t[0]
            if len(t) == 1:
                a.attribute_data[a.attributes[i]] = None
            else:
                a.attribute_data[a.attributes[i]] = t[1].split(',')

        h5.close()
        a.save(self.fname_out)

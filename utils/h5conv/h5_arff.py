import h5py, numpy, copy
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


    def get_contents(self):
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
            t = self.get_datatype(values)
            data[name] = numpy.array(values).astype(t)

        return {'names':names, 'ordering':copy.copy(names), 'data':data}



class H52ARFF(base.H5Converter):
    """Convert a file from HDF5 (spec of mldata.org) to ARFF

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/
    """

    def run(self):
        a = arff.ArffFile()
        data = self.get_contents()
        a.data = data['data']
        a.attributes = data['names']

        h5 = h5py.File(self.fname_in, 'r')
        a.relation = h5.attrs['name']
        a.comment = h5.attrs['comment']

        # handle arff types
        if '/data_descr/types' in h5:
            types = h5['/data_descr/types'][:]
        else:
            types = []
            for name in a.attributes:
                if name.startswith('int') or name.startswith('double'):
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

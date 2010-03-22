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
        return types


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
            arr = numpy.array(values)
            try:
                data[name] = arr.astype(numpy.int)
            except ValueError:
                try:
                    data[name] = arr.astype(numpy.double)
                except ValueError:
                    data[name] = arr.astype(self.str_type)

        return {'names':names, 'ordering':names, 'data':data}



class H52ARFF():
    """Convert a file from HDF5 (spec of mldata.org) to ARFF

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/

    @ivar fname_in: filename to read data from
    @type fname_in: string
    @ivar fname_out: filename to write converted data to
    @type fname_out: string

    """

    def __init__(self, fname_in, fname_out):
        self.fname_in = fname_in
        self.fname_out = fname_out


    def run(self):
        """Run the actual conversion process.

        @param in_fname: filename to read data from
        @type in_fname: string
        @param out_fname: filename to write converted data to
        @type out_fname: string
        """
        a = arff.ArffFile()
        h = h5py.File(self.fname_in, 'r')

        a.relation = h.attrs['name']
        a.comment = h.attrs['comment']
        a.attributes = list(h['data_descr/names'])

        a.data = []
        for i in xrange(len(h['data/' + h['data_descr/ordering'][0]])):
            a.data.append([])
        for name in h['data_descr/ordering']:
            path = 'data/' + name
            for j in xrange(len(h[path])):
                a.data[j].append(h[path][j])

        for i in xrange(len(h['data_descr/types'])):
            t = h['data_descr/types'][i].split(':')
            a.attribute_types[a.attributes[i]] = t[0]
            if len(t) == 1:
                a.attribute_data[a.attributes[i]] = None
            else:
                a.attribute_data[a.attributes[i]] = t[1].split(',')

        h.close()
        a.save(self.fname_out)

import numpy, h5py, os, copy, numpy
from scipy.sparse import csc_matrix
import base

COMMENT = '# '
SEPERATOR = ','

class CSV2H5(base.H5Converter):
    """Convert a file from CSV to HDF5 (spec of mldata.org).

    @ivar attribute_names_first: if first line in CSV files shall be treated as attribute names
    @type attribute_names_first: boolean
    """

    def __init__(self, *args, **kwargs):
        super(CSV2H5, self).__init__(*args, **kwargs)
        self.seperator = SEPERATOR # maybe more flexible in the future
        self.attribute_names_first = False


    def _find_nan(self, value):
        """Find NaN values and make them proper numpy.nan.

        Used by map function in get_contents()

        @param value: value to check if it is NaN
        @type value: string
        """
        if value == '?':
            return numpy.nan
        else:
            # str() important! when run thru webserver it will be unicode
            # otherwise and somehow results somewhere in nan being converted
            # to string 'na'...
            return str(value)


    def get_contents(self):
        data = {}
        names = []
        ordering = []

        infile = open(self.fname_in, 'r')
        parsed = []
        for line in infile:
            l = line.strip().split(self.seperator)
            if self.attribute_names_first:
                names = l
                self.attribute_names_first = False
            else:
                l = map(self._find_nan, l)
                parsed.append(l)
        infile.close()
        A = numpy.matrix(parsed).T

        for i in xrange(A.shape[0]):
            items = A[i].tolist()[0]
            t = self.get_datatype(items)
            if t == numpy.int32:
                name = 'int' + str(i)
            elif t == numpy.double:
                name = 'double' + str(i)
            else:
                name = 'str' + str(i)
            data[name] = numpy.array(items).astype(t)
            ordering.append(name)

        if not names:
            names = copy.copy(ordering)
        return {'names':names, 'ordering':ordering, 'data':data}



class H52CSV(base.H5Converter):
    """Convert a file from HDF5 (spec of mldata.org) to CSV."""

    def __init__(self, *args, **kwargs):
        super(H52CSV, self).__init__(*args, **kwargs)
        self.seperator = SEPERATOR # maybe more flexible in the future


    def run(self):
        csv = open(self.fname_out, 'w')
        try:
            contents = self.get_contents()
            for i in xrange(len(contents['data'])):
                line = map(str, contents['data'][i])
                if 'label' in contents:
                    label = map(str, contents['label'][i])
                    label = self.seperator.join(label)
                    line.insert(0, label)
                csv.write(self.seperator.join(line) + "\n")
        except KeyError, e:
            csv.close()
            os.remove(self.fname_out)
            raise KeyError(e)
        else:
            csv.close()

        return True

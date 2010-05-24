import numpy, h5py, os
from scipy.sparse import csc_matrix
import base

COMMENT = '# '
SEPERATOR = ','

class CSV2H5(base.H5Converter):
    """Convert a file from CSV to HDF5 (spec of mldata.org)."""

    def __init__(self, *args, **kwargs):
        super(CSV2H5, self).__init__(*args, **kwargs)
        self.seperator = SEPERATOR # maybe more flexible in the future


    def get_data(self):
        data = {}
        names = []
        ordering = []

        infile = open(self.fname_in, 'r')
        parsed = []
        for line in infile:
            parsed.append(line.strip().split(self.seperator))
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
            names.append(name)
            ordering.append(name)


        return {'names':names, 'ordering':names, 'data':data}



class H52CSV(base.H5Converter):
    """Convert a file from HDF5 (spec of mldata.org) to CSV."""

    def __init__(self, *args, **kwargs):
        super(H52CSV, self).__init__(*args, **kwargs)
        self.seperator = SEPERATOR # maybe more flexible in the future



    def run(self):
        csv = open(self.fname_out, 'w')
        try:
            data = self.get_data()
            for line in data['data']:
                csv.write(self.seperator.join(line) + "\n")
        except KeyError, e:
            csv.close()
            os.remove(self.fname_out)
            raise KeyError(e)
        else:
            csv.close()

        return True

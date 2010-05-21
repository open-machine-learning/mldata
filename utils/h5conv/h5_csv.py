import numpy, h5py, os
from scipy.sparse import csc_matrix
import base

COMMENT = '# '
SEPERATOR = ','

class CSV2H5(base.H5Converter):
    """Convert a file from CSV to HDF5 (spec of mldata.org).
    """

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

    def run(self):
        """Run the actual conversion process."""
        self.seperator = SEPERATOR # maybe more flexible in the future
        h5 = h5py.File(self.fname_in, 'r')
        csv = open(self.fname_out, 'w')

#        csv.write(COMMENT + h5.attrs['name'] + "\n")
#        csv.write(COMMENT + "MLDATA Version " + h5.attrs['mldata'] + ", see http://mldata.org\n")
#        csv.write(COMMENT + h5.attrs['comment'] + "\n")
        try:
            data = self.get_outdata(h5)
            for line in data:
                csv.write(self.seperator.join(line) + "\n")
        except KeyError, e:
            h5.close()
            csv.close()
            os.remove(self.fname_out)
            raise KeyError(e)
        else:
            h5.close()
            csv.close()

        return True

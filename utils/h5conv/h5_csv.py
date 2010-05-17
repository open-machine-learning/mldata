import numpy, h5py, os
from scipy.sparse import csc_matrix
import base

COMMENT = '# '


class H52CSV(base.H5Converter):
    """Convert a file from HDF5 (spec of mldata.org) to CSV."""

    def _write_label_data(self, h5, csv):
        """Write 'simple' label + data structure.

        @param h5: HDF5 file
        @param csv: CSV file
        @return: if successful
        @rtype: boolean
        """
        labels = list(h5['/data/label'])
        num_lab = len(labels)
        if len(labels[0]) == 1:
            label_vector = True
        else:
            label_vector = False

        A = numpy.matrix(h5['/data/data']).T

        for i in xrange(A.shape[0]):
            line = []
            if label_vector:
                line.append(str(labels[i][0]))
            else:
                for j in xrange(num_lab):
                    line.append(str(labels[j][i]))
            for j in xrange(A.shape[1]):
                line.append(str(A[i, j]))
            csv.write(self.seperator.join(line) + "\n")

        return True


    def _write_multiple_sets(self, h5, csv):
        """Write 'complex' data structure.

        @param h5: HDF5 file
        @param csv: CSV file
        @return: if successful
        @rtype: boolean
        """
        names = list(h5['/data_descr/ordering'])
        data = []

        if 'data/int' in h5:
            len_int = len(h5['/data/int'])
        else:
            len_int = 0
        idx_int = 0

        if 'data/double' in h5:
            len_double = len(h5['/data/double'])
        else:
            len_double = 0
        idx_double = 0

        for name in names:
            if name in h5['/data']:
                data.append(h5['/data/' + name][...])
            elif name.startswith('int'):
                data.append(h5['/data/int'][idx_int])
                idx_int += 1
            elif name.startswith('double'):
                data.append(h5['/data/double'][idx_double])
                idx_double += 1
            else: # either int or double
                if len_int and idx_int < len_int and type(h5['/data/int'][idx_int][0]) == numpy.int32:
                    data.append(h5['/data/int'][idx_int])
                    idx_int += 1
                elif len_double and idx_double < len_double and type(h5['/data/double'][idx_double][0]) == numpy.double:
                    data.append(h5['/data/double'][idx_double])
                    idx_double += 1
                else:
                    raise AttributeError('Dunno how to handle dataset ' + name)

        # A = numpy.matrix(data).T.astype(str) triggers memory corruption
        if len(data) == 1:
            A = numpy.matrix(data[0]).T # only one data blob
        else:
            A = numpy.matrix(data).T

        for i in xrange(A.shape[0]):
            line = map(str, A[i].tolist()[0])
            csv.write(self.seperator.join(line) + "\n")


    def run(self):
        """Run the actual conversion process."""
        h5 = h5py.File(self.fname_in, 'r')
        csv = open(self.fname_out, 'w')
        self.seperator = ','

#        csv.write(COMMENT + h5.attrs['name'] + "\n")
#        csv.write(COMMENT + "MLDATA Version " + h5.attrs['mldata'] + ", see http://mldata.org\n")
#        csv.write(COMMENT + h5.attrs['comment'] + "\n")
        try:
            if 'label' in h5['/data']: # only labels + data
                self._write_label_data(h5, csv)
            else:
                self._write_multiple_sets(h5, csv)
        except KeyError, e:
            h5.close()
            csv.close()
            os.remove(self.fname_out)
            raise KeyError(e)
        else:
            h5.close()
            csv.close()

        return True

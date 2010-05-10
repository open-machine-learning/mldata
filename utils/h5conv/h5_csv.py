import numpy, h5py, os
from scipy.sparse import csc_matrix
import base

SEPERATOR = ','
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
            csv.write(SEPERATOR.join(line) + "\n")

        return True


    def _write_multiple_sets(self, h5, csv):
        """Write 'comples' data structure.

        @param h5: HDF5 file
        @param csv: CSV file
        @return: if successful
        @rtype: boolean
        """
        names = list(h5['data_descr/ordering'])
        first_name = h5['data_descr/ordering'][0]
        shape = h5['/data/' + first_name].shape
        xrange_i = xrange(shape[0])
        if len(shape) < 2: # only 1 vector per name
            for i in xrange_i:
                line = []
                print names
                for name in names:
                    print name
                    line.append(str(h5['/data/' + name][i]))
                csv.write(SEPERATOR.join(line) + "\n")
        else: # reconstruct matrix
            xrange_j = xrange(shape[1])
            data = []
            for i in xrange_i:
                data[i] = []

            for name in names:
                current = list(h5['/data/' + name])
                for i in xrange_i:
                    for j in xrange_j:
                        data[i].append(current[i][j])

            A = numpy.matrix(data).T
            for i in A.shape[0]:
                line = []
                for j in A.shape[1]:
                    line.append(str(A[i,j]))
                csv.write(SEPERATOR.join(line) + "\n")


    def run(self):
        """Run the actual conversion process."""
        h5 = h5py.File(self.fname_in, 'r')
        csv = open(self.fname_out, 'w')

#        csv.write(COMMENT + h5.attrs['name'] + "\n")
#        csv.write(COMMENT + "MLDATA Version " + h5.attrs['mldata'] + ", see http://mldata.org\n")
#        csv.write(COMMENT + h5.attrs['comment'] + "\n")
        if 'label' in h5['/data']: # only labels + data
            self._write_label_data(h5, csv)
        else:
            self._write_multiple_sets(h5, csv)

        h5.close()
        csv.close()
        return True

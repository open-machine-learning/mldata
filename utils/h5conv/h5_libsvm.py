import numpy, h5py, os
from scipy.sparse import csc_matrix
import base

class LIBSVM2H5():
    """Convert a file from LibSVM to HDF5."""

    def __init__(self, *args, **kwargs):
        """Constructor.

        @ivar offset_labels: indices for labels for each row
        @type offset_labels: list of integers
        """
        self.offset_labels = []


    def _explode_labels(self, label):
        """Explode labels to be prepended to data row.

        This is needed for multilabel support.

        @param label: labels read from data file
        @type label: list of characters
        @return: exploded labels
        @rtype: list of integers
        """
        label = numpy.double(''.join(label).split(','))
        ll = []
        if len(label) > 1:
            for l in label:
                ll.append([l, 1])
            self.offset_labels.append(int(max(label)))
        else:
            ll.append([0, label[0]])
            self.offset_labels.append(0)
        return ll


    def _parse_line(self, line):
        """Parse a LibSVM input line and return attributes.

        @param line: line to parse
        @type line: string
        @return: attributes in this line
        @rtype: list of attributes
        """
        state = 'label'
        idx = []
        val = []
        label = []
        attributes = []
        for c in line:
            if state == 'label':
                if c.isspace():
                    state = 'idx'
                    attributes.extend(self._explode_labels(label))
                else:
                    label.append(c)
            elif state == 'idx':
                if not c.isspace():
                    if c == ':':
                        state = 'preval'
                    else:
                        idx.append(c)
            elif state == 'preval':
                if not c.isspace():
                    val.append(c)
                    state = 'val'
            elif state == 'val':
                if c.isspace():
                    attributes.append([int(''.join(idx)) + self.offset_labels[-1], ''.join(val)])
                    idx = []
                    val = []
                    state = 'idx'
                else:
                    val.append(c)

        return attributes


    def get_matrix(self, fname):
        """Retrieves a SciPy Compressed Sparse Column matrix from file.

        @param fname: filename to retrieve matrix from
        @type fname: string
        @return: compressed sparse column matrix
        @rtype: scipy.sparse.csc_matrix
        """
        indices = []
        indptr = [0]
        data = []
        ptr = 0
        infile = open(fname, 'r')
        for line in infile:
            attributes = self._parse_line(line)
            for a in attributes:
                indices.append(int(a[0]))
                data.append(numpy.double(a[1]))
                ptr += 1
            indptr.append(ptr)
        infile.close()

        return csc_matrix((numpy.array(data), numpy.array(indices), numpy.array(indptr)))


    def run(self, in_fname, out_fname):
        """Run the actual conversion process.

        @param in_fname: filename to read data from
        @type in_fname: string
        @param out_fname: filename to write converted data to
        @type out_fname: string
        """

        self.offset_labels = []
        A = self.get_matrix(in_fname)
        h = h5py.File(out_fname, 'w')

        if A.nnz/numpy.double(A.shape[0]*A.shape[1]) < 0.5: # sparse
            h.create_dataset('attributes_indices', data=A.indices, compression=base.COMPRESSION)
            h.create_dataset('attributes_indptr', data=A.indptr, compression=base.COMPRESSION)
            h.create_dataset('attributes_data', data=A.data, compression=base.COMPRESSION)
            h.attrs['comment'] = 'libsvm sparse'
        else: # dense
            A = A.todense().T
            h.create_dataset('attributes', data=A, compression=base.COMPRESSION)
            h.attrs['comment'] = 'libsvm dense'

        attribute_names = ['dim 1', '...', 'dim ' + str(A.shape[1])]
        h.create_dataset('attribute_names', data=attribute_names, compression=base.COMPRESSION)

        # without str(), h5py might barf
        h.attrs['name'] = str(os.path.basename(out_fname).split('.')[0])
        h.attrs['mldata'] = base.VERSION_MLDATA

        h.close()

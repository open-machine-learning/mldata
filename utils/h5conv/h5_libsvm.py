import numpy, h5py, os
from scipy.sparse import csc_matrix
import base



class LIBSVM2H5(base.H5Converter):
    """Convert a file from LibSVM to HDF5."""

    def __init__(self, *args, **kwargs):
        """Constructor.

        @ivar labels_maxidx: highest index for a label
        @type labels_maxidx: integer
        @ivar is_multilabel: if data is of type multilabel
        @type is_multilabel: boolean
        """
        super(LIBSVM2H5, self).__init__(*args, **kwargs)
        self.labels_maxidx = 0
        self.is_multilabel = False


    def _scrub_labels(self, labels):
        """Convert labels to doubles and determine max index

        @param labels: labels read from data file
        @type labels: list of characters
        @return: labels converted to double
        @rtype: list of integer
        """
        str_labels = ''.join(labels)
        if not self.is_multilabel and str_labels.find(',') == -1:
            self.labels_maxidx = 0
            return [numpy.double(str_labels)]
        else:
            self.is_multilabel = True
            lab = str_labels.split(',')
            for i in xrange(len(lab)):
                if not lab[i]:
                    lab[i] = 0
                else:
                    # int conversion to prevent error msg
                    lab[i] = int(float((lab[i])))
                if lab[i] > self.labels_maxidx:
                    self.labels_maxidx = lab[i]
            return lab


    def _parse_line(self, line):
        """Parse a LibSVM input line and return attributes.

        @param line: line to parse
        @type line: string
        @return: variables in this line
        @rtype: list of variables
        """
        state = 'label'
        idx = []
        val = []
        labels = []
        variables = []
        for c in line:
            if state == 'label':
                if c.isspace():
                    state = 'idx'
                    labels = self._scrub_labels(labels)
                else:
                    labels.append(c)
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
                    variables.append([int(''.join(idx)), ''.join(val)])
                    idx = []
                    val = []
                    state = 'idx'
                else:
                    val.append(c)

        return {'labels':labels, 'variables':variables}


    def get_matrix(self):
        """Retrieves a SciPy Compressed Sparse Column matrix from file.

        @return: compressed sparse column matrix
        @rtype: scipy.sparse.csc_matrix
        """
        self.labels_idx = []
        parsed = []
        infile = open(self.fname_in, 'r')
        for line in infile:
            parsed.append(self._parse_line(line))
        infile.close()
        self.labels_idx = range(self.labels_maxidx + 1)

        indices = []
        indptr = [0]
        data = []
        ptr = 0
        for i in xrange(len(parsed)):
            if len(parsed[i]['labels']) > 1: # multi label -> values are indices
                for idx in parsed[i]['labels']:
                    indices.append(int(idx))
                    data.append(1.)
                    ptr += 1
            else: # only single label -> value is actual value
                indices.append(0)
                data.append(numpy.double(parsed[i]['labels'][0]))
                ptr += 1

            for v in parsed[i]['variables']:
                indices.append(int(v[0]) + self.labels_maxidx)
                data.append(numpy.double(v[1]))
                ptr += 1
            indptr.append(ptr)

        return csc_matrix((numpy.array(data), numpy.array(indices), numpy.array(indptr)))


    def get_comment(self):
        return 'LibSVM'


    def get_data(self):
        A = self.get_matrix()
        data = {}
        if A.nnz/numpy.double(A.shape[0]*A.shape[1]) < 0.5: # sparse
            data['indices'] = A.indices
            data['indptr'] = A.indptr
            data['data'] = A.data
            ordering = ['indices', 'indptr', 'data']
        else: # dense
            data['data'] = A.todense()
            ordering = ['data']

        names = []
        for i in xrange(A.shape[0]):
            names.append('dim' + str(i))

        return {'ordering':ordering, 'names':names, 'data':data}

import numpy, h5py, os
from scipy.sparse import csc_matrix
import base



class LibSVM2H5(base.H5Converter):
    """Convert a file from LibSVM to HDF5."""

    def __init__(self, *args, **kwargs):
        """Constructor.

        @ivar label_maxidx: highest index for a label
        @type label_maxidx: integer
        @ivar is_multilabel: if data is of type multilabel
        @type is_multilabel: boolean
        """
        super(LibSVM2H5, self).__init__(*args, **kwargs)
        self.label_maxidx = 0
        self.is_multilabel = False


    def _scrub_labels(self, label):
        """Convert labels to doubles and determine max index

        @param label: labels read from data file
        @type label: list of characters
        @return: labels converted to double
        @rtype: list of integer
        """
        str_label = ''.join(label)
        if not self.is_multilabel and str_label.find(',') == -1:
            self.label_maxidx = 0
            return [numpy.double(str_label)]
        else:
            self.is_multilabel = True
            lab = str_label.split(',')
            for i in xrange(len(lab)):
                if not lab[i]:
                    lab[i] = 0
                else:
                    # int conversion to prevent error msg
                    lab[i] = int(float((lab[i])))
                if lab[i] > self.label_maxidx:
                    self.label_maxidx = lab[i]
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
        label = []
        variables = []
        for c in line:
            if state == 'label':
                if c.isspace():
                    state = 'idx'
                    label = self._scrub_labels(label)
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
                    variables.append([int(''.join(idx)), ''.join(val)])
                    idx = []
                    val = []
                    state = 'idx'
                else:
                    val.append(c)

        return {'label':label, 'variables':variables}


    def _get_parsed_data(self):
        """Retrieves a SciPy Compressed Sparse Column matrix and labels from file.

        @return: compressed sparse column matrix + labels
        @rtype: list of scipy.sparse.csc_matrix and label tuple/2-d tuple (multilabel)
        """
        parsed = []
        infile = open(self.fname_in, 'r')
        for line in infile:
            parsed.append(self._parse_line(line))
        infile.close()

        indices_var = []
        indices_lab = []
        indptr_var = [0]
        indptr_lab = [0]
        ptr_var = 0
        ptr_lab = 0
        data_var = []
        data_lab = []
        label = []
        for i in xrange(len(parsed)):
            if self.is_multilabel: # -> values are indices
                for idx in parsed[i]['label']:
                    indices_lab.append(int(idx))
                    data_lab.append(1.)
                    ptr_lab += 1
                indptr_lab.append(ptr_lab)
            else: # only single label -> value is actual value
                label.append(parsed[i]['label'])

            for v in parsed[i]['variables']:
                indices_var.append(int(v[0]) - 1) # -1: (multi)label idx
                data_var.append(numpy.double(v[1]))
                ptr_var += 1
            indptr_var.append(ptr_var)

        if self.is_multilabel:
            label = csc_matrix(
                (numpy.array(data_lab), numpy.array(indices_lab), numpy.array(indptr_lab))
            ).todense().T.tolist()
        else:
            label = numpy.matrix(label).tolist()

        return (
            csc_matrix(
                (numpy.array(data_var), numpy.array(indices_var), numpy.array(indptr_var))
            ),
            label,
        )


    def get_comment(self):
        return 'LibSVM'


    def get_contents(self):
        (A, label) = self._get_parsed_data()
        data = {}
        if A.nnz/numpy.double(A.shape[0]*A.shape[1]) < 0.5: # sparse
            data['indices'] = A.indices
            data['indptr'] = A.indptr
            data['data'] = A.data
            ordering = ['label', 'indices', 'indptr', 'data']
        else: # dense
            data['data'] = A.todense()
            ordering = ['label', 'data']

#        names = []
#        for i in xrange(A.shape[0]):
#            try:
#                row = A.todense()[i].tolist()[0]
#            except AttributeError: # isn't sparse
#                row = A[i].tolist()[0]
#
#            dtype = self.get_datatype(row)
#            if dtype == numpy.int32:
#                pre = 'int'
#            elif dtype == numpy.double:
#                pre = 'double'
#            else:
#                pre = 'str'
#            names.append(pre + str(i))

        return {
            'ordering': ordering,
            'names': ordering,
            'data': data,
            'label': label,
        }


class H52LibSVM(base.H5Converter):
    """Convert a file from LibSVM to HDF5."""

    def run(self):
        libsvm = open(self.fname_out, 'w')
        try:
            contents = self.get_contents()
            print contents['label']
            if len(contents['label'][0]) == 1:
                is_multilabel = False
            else:
                is_multilabel = True

            for i in xrange(len(contents['data'])):
                out = []
                if is_multilabel:
                    labels = []
                    for j in xrange(len(contents['label'][i])):
                        if contents['label'][i][j] == 1:
                            labels.append(str(j))
                    out.append(','.join(labels))
                else:
                    out.append(str(contents['label'][i][0]))
                for j in xrange(len(contents['data'][i])):
                    out.append(str(j+1) + ':' + str(contents['data'][i][j]))
                libsvm.write(" ".join(out) + "\n")
        except KeyError, e:
            libsvm.close()
            os.remove(self.fname_out)
            raise KeyError(e)
        else:
            libsvm.close()

        return True

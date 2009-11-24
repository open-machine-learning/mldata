"""
Convert from and to HDF5

Currently supported formats:

to hdf5
LibSVM
ARFF

from hdf5
ARFF
"""

import h5py, numpy

NAME = 'hdf5conv'
VERSION = '0.1'
VERSION_MLDATA = '0'


def progress(msg):
    print ' -> ' + msg



class Converter():
    def __init__(self, in_filename, out_filename):
        self.in_filename = in_filename
        self.out_filename = out_filename
        self.attrs = {}

    def run(self):
        print 'Not implemented yet!'

    def write_hdf5(self, *args, **kwargs):
        progress('writing out-file ' + self.out_filename)
        h = h5py.File(self.out_filename, 'w')

        progress('writing datasets')
        for key, val in kwargs.iteritems():
            h.create_dataset(key, data=numpy.array(val))

        progress('writing attributes')
        for key, val in self.attrs.iteritems():
            h.attrs[key] = val
        h.attrs['mldata'] = VERSION_MLDATA

        h.close()
        return True



class LibSVM2HDF5(Converter):
    def run(self):
        return False
        labels = []
        features = []

        infile = open(self.in_filename, 'r')
        progress('reading in-file ' + self.in_filename)
        for line in infile:
            items = line.strip().split(' ')
            items.remove('')

            labels.append(numpy.double(items.pop(0)))

            values = []
            for item in items:
                values.append(numpy.double(item.split(':')[1]))
            features.append(values)

        infile.close()

        self.attrs['name'] = 'foobar'
        progress('named as ' + self.attrs['name'])
        self.attrs['task'] = 'classification'
        progress('defined as task ' + self.attrs['task'])

        label_names = ''
        progress('no names for labels found...')
        feature_names = ''
        progress('no names for features found...')

        return self.write_hdf5(attr=attr,
            labels=labels, label_names=label_names,
            features=features, feature_names=feature_names)



class ARFF2HDF5(Converter):
    def run(self):
        import arff
        a = arff.ArffFile.load(self.in_filename)

        progress('gathering HDF5 attributes')
        self.attrs['name'] = a.relation
        self.attrs['comment'] = a.comment

        progress('gathering HDF5 datasets')
        attribute_names = a.attributes
        attributes = a.data
        attribute_types = []
        for key, val in a.attribute_types.iteritems():
            if a.attribute_data[key]:
                data = ','.join(a.attribute_data[key])
                val = val + '(' + data + ')'
            val = key + ':' + val
            attribute_types.append(val)

        return self.write_hdf5(
            attribute_names=attribute_names, attribute_types=attribute_types,
            attributes=attributes)


class HDF52ARFF(Converter):
    def run(self):
        import arff
        a = arff.ArffFile()
        h = h5py.File(self.in_filename, 'r')

        progress('retrieving from HDF5 attributes')
        a.relation = h.attrs['name']
        a.comment = h.attrs['comment']

        progress('retrieving from HDF5 datasets')
        a.data = h['attributes']
        a.attributes = h['attribute_names']
        for htype in h['attribute_types']:
            sep = htype.find(':')
            attr = htype[:sep]
            type = htype[sep+1:]
            idx = type.find('(')
            if idx != -1:
                # +1/-1 -> commas
                data = type[idx+1:-1].split(',')
                type = type[:idx]
            else:
                data = None
            a.attribute_types[attr] = type
            a.attribute_data[attr] = data

        a.save(self.out_filename)
        return True


"""
Convert from and to HDF5 (spec of mldata.org)

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
NUM_EXTRACT = 23


def progress(msg):
    """Print the given message with some kind of progress indicator."""
    #print ' -> ' + msg
    pass



class Converter():
    """Base class for conversion"""

    def __init__(self, in_filename, out_filename):
        """Constructor takes two arguments:

        filename of in-file, filename of out-file
        """
        self.in_filename = in_filename
        self.out_filename = out_filename
        self.attrs = {
            'mldata': VERSION_MLDATA,
            'name': '',
            'comment': '',
        }

    def run(self):
        """Run the actual conversion process.

        'Abstract base method' to be implemented by child classes.
        """
        raise Exception('Not implemented yet!')

    def write_hdf5(self, *args, **kwargs):
        """Write an HDF file (spec of mldata.org)."""
        progress('writing out-file ' + self.out_filename)
        h = h5py.File(self.out_filename, 'w')

        progress('writing datasets')
        for key, val in kwargs.iteritems():
            if val: # h5py doesn't like writing empty datasets
                h.create_dataset(key, data=numpy.array(val))

        progress('writing attributes')
        for key, val in self.attrs.iteritems():
            h.attrs[key] = val

        h.close()
        return True



class LibSVM2HDF5(Converter):
    """Convert a file from LibSVM to HDF5

    This is simple enough, so it doesn't need its own module.
    """

    def run(self):
        """Run the actual conversion process."""
        progress('reading in-file ' + self.in_filename)
        infile = open(self.in_filename, 'r')
        attributes = []
        #attributes = numpy.array([])
        for line in infile:
            items = line.strip().split(' ')
            try:
                items.remove('')
            except ValueError:
                pass

            attribute = []
            # label/target
            attribute.append(numpy.double(items.pop(0)))
            # features
            prev_idx = 0
            for item in items:
                idx, val = item.split(':')
                if int(idx) > (prev_idx + 1):
                    attribute.append(0) # sparse values!
                prev_idx = int(idx)
                attribute.append(numpy.double(val))
            attributes.append(attribute)
        infile.close()

        progress('emtpy values for attribute_names, attribute_types, name, comment.')

        return self.write_hdf5(attributes=attributes)




class ARFF2HDF5(Converter):
    """Convert a file from ARFF to HDF5 (spec of mldata.org).

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/
    """

    def run(self):
        """Run the actual conversion process."""
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
    """Convert a file from HDF5 (spec of mldata.org) to ARFF

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/
    """

    def run(self):
        """Run the actual conversion process."""
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

        h.close()
        a.save(self.out_filename)
        return True


def hdf5_extract(filename):
    """Get an extract from an HDF file."""
    h = h5py.File(filename, 'r')
    extract = {}

    attrs = ['mldata', 'name', 'comment']
    for attr in attrs:
        try:
            extract[attr] = h.attrs[attr]
        except KeyError:
            pass

    dsets = ['attribute_names', 'attribute_types']
    for dset in dsets:
        try:
            extract[dset] = h[dset][:]
        except KeyError:
            pass

    # only first NUM_EXTRACT items of attributes
    try:
        extract['attributes'] = []
        for i in xrange(NUM_EXTRACT):
            extract['attributes'].append(h['attributes'][i])
    except KeyError:
        pass

    h.close()
    return extract

import h5py
import arff, config


class ARFF2HDF5():
    """Convert a file from ARFF to HDF5 (spec of mldata.org).

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/
    """

    def run(self, in_fname, out_fname):
        """Run the actual conversion process."""
        a = arff.ArffFile.load(in_fname)
        h = h5py.File(out_fname, 'w')

        h.attrs['mldata'] = config.VERSION_MLDATA
        h.attrs['name'] = a.relation
        h.attrs['comment'] = a.comment
        h.create_dataset('attribute_names', data=a.attributes)
        h.create_dataset('attributes', data=a.data)

        attribute_types = []
        for key, val in a.attribute_types.iteritems():
            if a.attribute_data[key]:
                data = ','.join(a.attribute_data[key])
                val = val + '(' + data + ')'
            val = key + ':' + val
            attribute_types.append(val)
        h.create_dataset('attribute_types', data=attribute_types)

        h.close()


class HDF52ARFF():
    """Convert a file from HDF5 (spec of mldata.org) to ARFF

    It uses the module arff provided by the dataformat project:
    http://mloss.org/software/view/163/
    """

    def run(self, in_fname, out_fname):
        """Run the actual conversion process."""
        a = arff.ArffFile()
        h = h5py.File(in_fname, 'r')

        a.relation = h.attrs['name']
        a.comment = h.attrs['comment']
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
        a.save(out_fname)


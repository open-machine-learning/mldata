import h5py, os
import config

class UCI2HDF5():
    """Convert a file from UCI to HDF5."""

    def run(self, in_fname, out_fname):
        """Run the actual conversion process."""
        h = h5py.File(out_fname, 'w')

        names = '.'.join(in_fname.split('.')[:-1]) + '.names'
        f = open(names, 'r')
        h.attrs['comment'] = ''.join(f.readlines())
        f.close()

        f = open(in_fname, 'r')
        data = []
        for line in f.readlines():
            l = []
            for item in line.strip().split(','):
                l.append(item)
            data.append(l)
        f.close()
        h.create_dataset('attributes', data=data, compression=config.COMPRESSION)

        # without str(), h5py might barf
        h.attrs['name'] = str(os.path.basename(out_fname).split('.')[0])
        h.attrs['mldata'] = config.VERSION_MLDATA

        h.close()

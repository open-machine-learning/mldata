import h5py, os
import config

class UCI2HDF5():
    """Convert a file from UCI to HDF5."""

    def _get_comment(self, in_fname):
        name = '.'.join(in_fname.split('.')[:-1])
        if not name:
            name = '.'.join(in_fname.split('-')[:-1])

        f = open(name + '.names', 'r')
        comment = ''.join(f.readlines())
        f.close()
        return comment


    def _get_data(self, in_fname):
        f = open(in_fname, 'r')
        data = []
        for line in f:
            l = []
            for item in line.strip().split(','):
                if item:
                    l.append(item.strip())
            if l:
                data.append(l)
        f.close()
        return data


    def run(self, in_fname, out_fname):
        """Run the actual conversion process."""
        h = h5py.File(out_fname, 'w')

        h.attrs['comment'] = self._get_comment(in_fname)

        data = self._get_data(in_fname)
        if data:
            try:
                h.create_dataset('attributes', data=data, compression=config.COMPRESSION)
            except ValueError:
                # flatten data
                h.create_dataset('attributes', data=sum(data, []), compression=config.COMPRESSION)

        # without str(), h5py might barf
        h.attrs['name'] = str(os.path.basename(out_fname).split('.')[0])
        h.attrs['mldata'] = config.VERSION_MLDATA

        h.close()

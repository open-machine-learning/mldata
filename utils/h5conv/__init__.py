"""
Convert from and to HDF5 (spec of mldata.org)
"""


import h5py, numpy, os
from scipy.sparse import csc_matrix
from h5_arff import ARFF2H5, H52ARFF
from h5_libsvm import LIBSVM2H5
from h5_uci import UCI2H5
from h5_csv import H52CSV
import base



class HDF5():
    def __init__(self, *args, **kwargs):
        """Construct an HDF5 object.

        The object can convert, extract data, create task
        files and more.

        @ivar converter: actual converter object
        @type converter: depending on required conversion, e.g. ARFF2H5.
        """
        self.converter = None


    def convert(self, in_fname, in_format, out_fname, out_format):
        """Convert to/from HDF5.

        @param in_fname: name of in-file
        @type in_fname: string
        @param in_format: format of in-file
        @type in_format: string
        @param out_fname: name of out-file
        @type out_fname: string
        @param out_format: format of out-file
        @type out_format: string
        """

        self.converter = None
        if in_format == 'libsvm' and out_format == 'h5':
            self.converter = LIBSVM2H5(in_fname, out_fname)
        elif in_format == 'arff' and out_format == 'h5':
            self.converter = ARFF2H5(in_fname, out_fname)
        elif in_format == 'uci' and out_format == 'h5':
            self.converter = UCI2H5(in_fname, out_fname)
        elif in_format == 'h5':
            if out_format == 'arff':
                self.converter = H52ARFF(in_fname, out_fname)
            elif out_format == 'csv':
                self.converter = H52CSV(in_fname, out_fname)

        if not self.converter:
            raise RuntimeError('Unknown conversion pair %s to %s!' % (in_format, out_format))

        self.converter.run()



    def is_binary(self, fname):
        """Return true if the given filename is binary.

        @param fname: filename to check if binary
        @type fname: string
        @return: if file is binary
        @rtype: boolean
        """
        f = open(fname, 'rb')
        try:
            CHUNKSIZE = 1024
            while 1:
                chunk = f.read(CHUNKSIZE)
                if '\0' in chunk: # found null byte
                    f.close()
                    return 1
                if len(chunk) < CHUNKSIZE:
                    break # done
        finally:
            f.close()

        return 0


    def get_filename(self, orig):
        """Convert a given filename to something that indicates HDF5.

        @param orig: original filename
        @type orig: string
        @return: HDF5-ified filename
        @rtype: string
        """
        return orig + '.h5'


    def get_fileformat(self, fname):
        """Determine fileformat by given filenname.

        @param fname: filename to get format from
        @type fname: string
        @return: format of given file(name)
        @rtype: string
        """
        suffix = fname.split('.')[-1]
        if suffix == 'txt':
            return 'libsvm'
        elif suffix == 'arff':
            return suffix
        elif suffix == 'h5':
            return suffix
        elif suffix in ('bz2', 'gz'):
            presuffix = fname.split('.')[-2]
            if presuffix == 'tar':
                return presuffix + '.' + suffix
            return suffix
        else: # unknown
            return suffix


    def get_unparseable(self, fname):
        """Get data from unparseable files

        @param fname: filename to get data from
        @type fname: string
        @return: raw extract from unparseable file
        @rtype: dict with 'attribute' data
        """
        import tarfile, zipfile
        if zipfile.is_zipfile(fname):
            intro = 'ZIP archive'
            f = zipfile.ZipFile(fname)
            data = ', '.join(f.namelist())
            f.close()
        elif tarfile.is_tarfile(fname):
            intro = '(Zipped) TAR archive'
            f = tarfile.TarFile.open(fname)
            data = ', '.join(f.getnames())
            f.close()
        else:
            intro = 'Unparseable Data'
            if self.is_binary(fname):
                data = ''
            else:
                f = open(fname, 'r')
                i = 0
                data = []
                for l in f:
                    data.append(l)
                    i += 1
                    if i > base.NUM_EXTRACT:
                        break
                f.close()
                data = "\n".join(data)

        return {'attributes': [[intro, data]]}


    def get_extract(self, fname):
        """Get an extract of an HDF5 file.

        @param fname: filename to get get extract from
        @type fname: string
        @return: extract of an HDF5 file
        @rtype: dict with HDF5 attribute/dataset names as keys and their data as values
        """
        format = self.get_fileformat(fname)
        if format != 'h5':
            h5_fname = self.get_filename(fname)
            try:
                self.convert(fname, format, h5_fname, 'h5')
            except Exception:
                return self.get_unparseable(fname)
        else:
            h5_fname = fname

        h5file = h5py.File(h5_fname, 'r')
        extract = {}

        attrs = ['mldata', 'name', 'comment']
        for attr in attrs:
            try:
                extract[attr] = h5file.attrs[attr]
            except KeyError:
                pass

        try:
            extract['names'] = h5file['data_descr/names'][:]
        except KeyError:
            pass

        # only first NUM_EXTRACT items of attributes
        try:
            extract['data'] = []
            ne = base.NUM_EXTRACT

            if ('indptr' and 'indices') in h5file['data']:
                # taking all data takes to long for quick viewing, but having just
                # this extract may result in less columns displayed than indicated
                # by attributes_names
                data = h5file['data/data'][:h5file['data/indptr'][ne+1]]
                indices = h5file['data/indices'][:h5file['data/indptr'][ne+1]]
                indptr = h5file['data/indptr'][:ne+1]
                A=csc_matrix((data, indices, indptr)).todense().T
                extract['data'] = A[:ne].tolist()
            else:
                for dset in h5file['data']:
                    dset = 'data/' + dset
                    if type(h5file[dset][0]) == numpy.ndarray:
                        for i in xrange(len(h5file[dset])):
                            extract['data'].append(h5file[dset][i][:ne])
                    else:
                        extract['data'].append(h5file[dset][:ne])
                extract['data'] = numpy.matrix(extract['data']).T

            # convert from numpy array to list, if necessary
            t = type(extract['data'][0])
            if t == numpy.ndarray or t == numpy.matrix:
                extract['data'] = [y for x in extract['data'] for y in x.tolist()]
        except KeyError:
            pass
        except ValueError:
            pass
        except IndexError:
            pass

        h5file.close()
        return extract


    def get_num_instattr(self, fname):
        """Retrieve number of instances and number of attributes from given
        file.

        @param fname: filename to retrieve data from
        @type fname: string
        @return: number of instances and number of attributes
        @rtype: tuple containing 2 integers
        """
        h5file = h5py.File(fname, 'r')
        if not 'data' in h5file:
            instattr = (-1, -1)
        else:
            # FIXME!
            instattr = (-1, -1)

        h5file.close()
        return instattr


    def _get_splitnames(self, fnames):
        """Helper function to get names of splits.

        Get a name like test_idx, train_idx from given filenames.

        @param fnames: filenames to get splitnames from
        @type fnames: list of string
        @return: names of splits
        @rtype: list of strings
        """
        names = []
        for name in fnames:
            n = name.split(os.sep)[-1]
            if n.find('train') != -1 or n.find('.tr') != -1:
                names.append('train_idx')
            elif n.find('.val') != -1:
                names.append('validation_idx')
            elif n.find('test') != -1 or n.find('.t') != -1 or n.find('.r') != -1:
                names.append('test_idx')
            else:
                names.append(0)

        # replace unknown name by test if train exists or train if test exists
        if 0 in names:
            if 'train_idx' in names:
                names[names.index(0)] = 'test_idx'
            elif 'test_idx' in names:
                names[names.index(0)] = 'train_idx'

        return names


    def _get_splitdata(self, fnames):
        """Get split data.

        @param fnames: filenames of related data files
        @type fnames: list of strings
        """
        names = self._get_splitnames(fnames)
        data = {}
        offset = 0
        for i in xrange(len(fnames)):
            count = sum(1 for line in open(fnames[i]))
            if names[i] in data: # in case we have multiple train/test idx
                data[names[i]].extend(range(offset, offset+count))
            else:
                data[names[i]] = range(offset, offset+count)
            offset += count

        return data


    def create_taskfile(self, name, fnames):
        """Create a Task file, using HDF5.

        @param name: name of the Task item
        @type name: string
        @param fnames: names of files to contain Task data
        @type fnames: list of strings
        @return: name of created Task file
        @rtype: string
        """
        fname = self.get_filename(name)
        h5file = h5py.File(fname, 'w')

        group = h5file.create_group('/task')
        if self.converter and self.converter.labels_idx:
            group.create_dataset('label_dims', data=self.converter.labels_idx, compression=base.COMPRESSION)

        data = self._get_splitdata(fnames)
        for k,v in data.iteritems():
            group.create_dataset(k, data=v, compression=base.COMPRESSION)

        h5file.attrs['name'] = name
        h5file.attrs['mldata'] = base.VERSION_MLDATA
        h5file.attrs['comment'] = 'Task file'
        h5file.close()

        return fname

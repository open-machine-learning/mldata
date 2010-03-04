"""
Convert from and to HDF5 (spec of mldata.org)

Structure of the HDF5 Format
============================

This will be the generic storage for all kinds of data sets. The basic
abstraction is that a data set is a large collection of objects having
the same type, so to say a large array.

/mldata
 version of the file format
 Integer = 0
/name
 Name of the data set
 String
/comment
 Initial comment
 String
/attribute_names
 Nnames of the attributes
 Array of Strings
/attribute_types
 Description of the attribute types (see below)
 Array of Strings
/attributes
 as described by attribute_types
 Array of Objects


Attribute Types
---------------

We make a distinction between the actual binary format and the
attribute type stored in the file. For example, nominal data might be
stored as integers or even bytes for efficiency, although they are
mapped to symbolic names to the outside.

The attribute type is specified by a string which has to be parsed for
better flexibility.

Supported types are:

"NUMERIC"
Numerical values
Array of Numerical type

"NOMINAL(VALUE1, VALUE2, ...)"
Enumeration type
Aarray of small Integer types

"STRING"
Array of Strings

As we see more data types, more type descriptors will be added.


Split files and Tasks
=====================

Note that the distinction what is input/output, label/target depends
on the TASK, not on the data set itself!
We do have a mechanism in place to create automatic split files while slurping
datasets from other repositories, though. These datasets may be defined in the
split files:

/labels
 Index of labels/target for each data row
 Array of Integers
/testing|training|validation|whatever the slurper could derive from the dataset
 Indices of input/output/whatever task requires
 Array of Integers


Currently supported formats
===========================
to hdf5
LibSVM
ARFF
UCI

from hdf5
ARFF
"""


import h5py, numpy, os
from scipy.sparse import csc_matrix
from h5_arff import ARFF2H5, H52ARFF
from h5_libsvm import LIBSVM2H5
from h5_uci import UCI2H5
import config


class HDF5():
    def __init__(self, *args, **kwargs):
        """Construct an HDF5 object.

        The object can convert, extract data, create split
        files and much more.

        @ivar attrs: attributes of HDF5 file
        @type attrs: dict with keys mldata, name, comment
        @ivar converter: actual converter object
        @type converter: depending on required conversion, e.g. ARFF2H5.
        """
        self.attrs = {
            'mldata': config.VERSION_MLDATA,
            'name': '',
            'comment': '',
        }
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
            self.converter = LIBSVM2H5()
        elif in_format == 'arff' and out_format == 'h5':
            self.converter = ARFF2H5()
        elif in_format == 'uci' and out_format == 'h5':
            self.converter = UCI2H5()
        elif in_format == 'h5' and out_format == 'arff':
            self.converter = H52ARFF()
        if not self.converter:
            raise RuntimeError('Unknown conversion pair %s to %s!' % (in_format, out_format))

        self.converter.run(in_fname, out_fname)



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
                file = open(fname, 'r')
                i = 0
                data = []
                for line in file:
                    data.append(line)
                    i += 1
                    if i > config.NUM_EXTRACT:
                        break
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

        h = h5py.File(h5_fname, 'r')
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
            ne = config.NUM_EXTRACT
            if 'attributes_indptr' in h: # sparse
                # taking all data takes to long for quick viewing, but having just
                # this extract may result in less columns displayed than indicated
                # by attributes_names
                data = h['attributes_data'][:h['attributes_indptr'][ne+1]]
                indices = h['attributes_indices'][:h['attributes_indptr'][ne+1]]
                indptr = h['attributes_indptr'][:ne+1]
                A=csc_matrix((data, indices, indptr)).todense().T
                for i in xrange(ne):
                    extract['attributes'].append(A[i].tolist()[0])

            else: # dense
                A=h['attributes']
                for i in xrange(ne):
                    extract['attributes'].append(A[i])
        except KeyError:
            pass
        except ValueError:
            pass

        h.close()
        return extract


    def create_split(self, fname, name, indices):
        """Create a split file, using HDF5.

        @param fname: name of the split file
        @type fname: string
        @param name: name of the Task item
        @type name: string
        @param indices: split indices
        @type indices: dict
        """
        h = h5py.File(fname, 'w')

        if self.converter.offset_labels and max(self.converter.offset_labels) > 0:
            h.create_dataset('labels', data=self.converter.offset_labels, compression=config.COMPRESSION)

        for k,v in indices.iteritems():
            data = []
            for row in v:
                r = []
                for col in row:
                    r.append(numpy.double(col))
                data.append(r)
            h.create_dataset(k, data=data, compression=config.COMPRESSION)

        h.attrs['name'] = name
        h.attrs['mldata'] = config.VERSION_MLDATA
        h.attrs['comment'] = 'split file'
        h.close()

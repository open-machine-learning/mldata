#!/usr/bin/env python
"""
Convert from and to HDF5

Currently supported formats:

to hdf5
LibSVM
ARFF
UCI

from hdf5
ARFF
"""

import sys, os
# adjust if you move this file elsewhere
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../utils'))
import hdf5conv

def usage():
    print """Usage:
""" + sys.argv[0] + """ <in-filename> <in format> <out-filename> <out format>

Supported conversions are:
libsvm -> hdf5
arff -> hdf5
uci -> hdf5
hdf5 -> arff
"""


if __name__ == "__main__":
    argc = len(sys.argv)
    if  argc < 5:
        usage()
        sys.exit(1)

    h = hdf5conv.HDF5()
    h.convert(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])


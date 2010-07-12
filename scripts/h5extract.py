#!/usr/bin/env python
"""
Print an extract of an HDF5 file, similar to website output
"""

import sys, os
import ml2h5

def usage():
    print """Usage: """ + sys.argv[0] + """ <filename>"""


if __name__ == "__main__":
    argc = len(sys.argv)
    if  argc < 2:
        usage()
        sys.exit(1)

    h = ml2h5.HDF5()
    print h.get_extract(sys.argv[1])

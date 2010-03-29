#!/usr/bin/env python
"""
Print an extract of an HDF5 file, similar to website output
"""

import sys, os
# adjust if you move this file elsewhere
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../utils'))
import h5conv

def usage():
    print """Usage: """ + sys.argv[0] + """ <filename>"""


if __name__ == "__main__":
    argc = len(sys.argv)
    if  argc < 2:
        usage()
        sys.exit(1)

    h = h5conv.HDF5()
    print h.get_extract(sys.argv[1])

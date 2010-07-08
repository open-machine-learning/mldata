#!/usr/bin/env python
"""
Convert from and to HDF5
"""

import sys, os, getopt
# adjust if you move this file elsewhere
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../utils'))
import h5conv

def usage():
    msg = ["""Usage: """ + sys.argv[0] + """ [options] <in-filename> <out-filename>

Options:

-s, --seperator
    Seperator to use to seperate variables in examples. Default is ','

-v, --verfiy
    Verify the converted data

-f, --first-line-attribute-names
    First line contains attributes names (for CSV)

-i, --format-in
    File format of in-file (if auto-detection fails)

-o, --format-out
    file format of out-file (if auto-detection fails)


    Supported conversions are:
"""]

    for item in h5conv.TOH5.iterkeys():
        msg.append('    ' + item + ' -> ' + 'h5')
    msg.append('')
    for item in h5conv.FROMH5.iterkeys():
        msg.append('    h5 -> ' + item)

    print "\n".join(msg)


class Options:
    """Option.

    Should not be instantiated.

    @cvar seperator: seperator to seperate variables in examples
    @type output: string
    @cvar verify: if converted data shall be verified against input data
    @type verify: boolean
    @cvar attribute_names_first: if first line in CSV files shall be treated as attribute names
    @type attribute_names_first: boolean
    @cvar format_in: file format of in-file
    @type format_in: string
    @cvar format_out: file format of out-file
    @type format_out: string
    """
    seperator = None
    verify = False
    attribute_names_first = False
    format_in = None
    format_out = None


def rm_opt(option, value=None):
    """Remove given option and value from sys.argv.

    @param option: option to remove
    @type option: string
    @param value: value to remove
    @type value: string
    """
    if not value:
        sys.argv.remove(option)
        return

    try:
        sys.argv.remove(option + value)
    except ValueError:
        try:
            sys.argv.remove(option)
            sys.argv.remove(value)
        except ValueError:
            sys.argv.remove(option + '=' + value)


def parse_options():
    """Parse given options."""
    try:
        opts, args = getopt.getopt(sys.argv[1:], 's:vfi:o:',
            ['seperator=', 'verify', 'first-line-attribute-names',
            'format-in=', 'format-out='])
    except getopt.GetoptError, err: # print help information and exit
        print str(err) + "\n"
        usage()
        sys.exit(1)

    for o, a in opts:
        if o in ('-s', '--seperator'):
            Options.seperator = a
        elif o in ('-v', '--verify'):
            Options.verify = True
        elif o in ('-f', '--first-line-attribute-names'):
            Options.attribute_names_first = True
        elif o in ('-i', '--format-in'):
            Options.format_in = a
        elif o in ('-o', '--format-out'):
            Options.format_out = a
        else:
            print 'Unhandled option: ' + o
            sys.exit(2)
        rm_opt(o, a)


if __name__ == "__main__":
    argc = len(sys.argv)
    if  argc < 3:
        usage()
        sys.exit(1)

    parse_options()
    h = h5conv.HDF5()

    if sys.argv[2] == 'h5':
        seperator = None
    elif Options.seperator:
        seperator = Options.seperator
    else:
        seperator = h5conv.fileformat.infer_seperator(sys.argv[1])

    h.convert(
        sys.argv[1], sys.argv[2],
        format_in=Options.format_in, format_out=Options.format_out,
        seperator=seperator,
        verify=Options.verify,
        attribute_names_first=Options.attribute_names_first
    )


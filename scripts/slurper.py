#!/usr/bin/env python
"""
Slurp data objects from the interwebz and add them to the repository
"""

import getopt, sys, os

# adjust if you move this file elsewhere
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'mldata.settings'

from utils.slurper import Options, SLURPERS
for name in SLURPERS:
    exec('from utils.slurper.' + name.lower() + ' import ' + name)


def get_sources():
    sources = []
    for i in xrange(len(SLURPERS)):
        sources.append('        ' + str(i) + ' - ' + eval(SLURPERS[i]).url)
    return "\n".join(sources)


def usage():
    """Print usage of slurper."""
    print 'Usage: ' + sys.argv[0] + ''' [options]

Options:

-o, --output
        target directory for downloads
        default: ''' + Options.output + '''

-s, --source
        source of where to slurp data from. Available sources are:
''' + get_sources() + '''
        default: ''' + str(Options.source) + '''

-v, --verbose
        enable verbose mode
        default: ''' + str(Options.verbose) + '''

-d, --download-only
        only download data, don't add to repository
        default: ''' + str(Options.download_only) + '''

-a, --add-only
        only add to repository, don't download
        default: ''' + str(Options.add_only) + '''

-c, --convert-exist
        convert data files of existing datasets, but don't add them; implies
        download, excludes add-only.
        default: ''' + str(Options.convert_exist) + '''

-f, --force-download
        download even if file already exists
        default: ''' + str(Options.force_download) + '''

-h, --help
        show this help message and exit
'''


def parse_options():
    """Parse options given to slurper."""
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'o:s:vdacfh',
            ['output=', 'source=', 'verbose', 'download-only',
            'add-only', 'convert-exist', 'force-download', 'help'])
    except getopt.GetoptError, err: # print help information and exit
        print str(err) + "\n"
        usage()
        sys.exit(1)

    options = Options()
    for o, a in opts:
        if o in ('-o', '--output'):
            if a.startswith(os.sep): # absolute
                options.output = a
            else: # relative
                options.output = os.path.join(os.getcwd(), a)
        elif o in ('-s', '--source'):
            a = int(a)
            if a > len(SLURPERS)-1:
                usage()
                sys.exit(0)
            else:
                options.source = a
        elif o in ('-v', '--verbose'):
            options.verbose = True
        elif o in ('-d', '--download-only'):
            options.download_only = True
        elif o in ('-a', '--add-only'):
            options.add_only = True
        elif o in ('-c', '--convert-exist'):
            options.convert_exist = True
        elif o in ('-f', '--force-download'):
            options.force_download = True
        elif o in ('-h', '--help'):
            usage()
            sys.exit(0)
        else:
            print 'Unhandled option: ' + o
            sys.exit(2)

    if options.add_only and options.download_only:
        print 'Options add-only and download-only are mutually exclusive, please reconsider!'
        sys.exit(3)

    if options.add_only and options.convert_exist:
        print 'Options add-only and convert-exist are mutually exclusive, please reconsider!'
        sys.exit(3)

    if options.download_only and options.convert_exist:
        print 'Options download-only and convert-exist are mutually exclusive, please reconsider!'
        sys.exit(3)

    if not os.path.exists(options.output):
        print 'Creating output directory ' + options.output
        os.mkdir(options.output)

    return options


if __name__ == '__main__':
    options = parse_options()

    if not options.source in xrange(len(SLURPERS)):
        for name in SLURPERS:
            slurper = eval(name)(options=options)
            slurper.run()
    else:
        try:
            slurper = eval(SLURPERS[options.source])(options=options)
        except IndexError:
            print 'Unknown slurping source!'
            sys.exit(1)
        slurper.run()

    sys.exit(0)

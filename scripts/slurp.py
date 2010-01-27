#!/usr/bin/env python
"""
Slurp data objects from the interwebz and add them to the repository
"""

import getopt, sys, os, urllib
from HTMLParser import HTMLParser


class LibSVMToolsHTMLParser(HTMLParser):
    datasets = []
    current = None
    is_name = False
    is_description = False
    is_file = False
    in_ul = False


    def _reset(self):
        self.current = None
        self.is_name = False
        self.is_description = False
        self.is_file = False
        self.in_ul = False

    def handle_starttag(self, tag, attrs):
        if tag == 'h2': # new data starts here
            self.is_name = True
            self.current = {
                'name': '',
                'description': '',
                'files': [],
            }
        elif tag == 'ul' and not self.in_ul:
            self.in_ul = True
        elif tag == 'li' and not self.is_file:
            self.is_description = True
        elif tag == 'ul' and self.in_ul:
            self.is_description = False
            self.is_file = True
        elif tag == 'a' and self.is_file:
            self.current['files'].append(attrs[0][1])


    def handle_endtag(self, tag):
        if tag == 'h2':
            self.is_name = False
        elif tag == 'ul' and self.current: # new data ends here
            self.datasets.append(self.current)
            self._reset()


    def handle_data(self, data):
        if self.is_name:
            self.current['name'] = data
        elif self.is_description:
            self.current['description'] += data


class Slurper:
    source = None
    output = None

    def fromfile(self, name):
        f = open(name, 'r')
        data = f.read()
        f.close()
        return data


    def run(self):
        write('Slurping from ' + self.source + '.')

        self.output = Options.output + os.path.sep +\
            self.__class__.__name__ + os.path.sep
        if not os.path.exists(self.output):
            os.mkdir(self.output)

        self.download()
        if not Options.download_only:
            self.add()

    def download(self):
        raise NotImplementedError('Abstract method!')

    def add(self):
        write('Adding to repository.')


class LibSVMTools(Slurper):
    source = 'http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/'

    def download(self):
        write('Downloading from section binary.')
        parser = LibSVMToolsHTMLParser()
        response = urllib.urlopen(self.source + 'binary.html')
        parser.feed(''.join(response.readlines()))
        #parser.feed(self.fromfile('binary.html'))
        response.close()
        parser.close()
        for d in parser.datasets:
            for f in d['files']:
                src = self.source + f
                dst = self.output + f
                if not Options.force_download and os.path.exists(dst):
                    write(dst + ' already exists, skipping download.')
                else:
                    dst_dir = os.path.dirname(dst)
                    if not os.path.exists(dst_dir):
                        os.mkdir(dst_dir)
                    write('Downloading ' + src + ' to ' + dst + '.')
                    urllib.urlretrieve(src, dst)
        write('...')


        write('Downloading from section multi-class.')
        write('Downloading from section regression.')
        write('Downloading from section multi-label.')


class Weka(Slurper):
    source = 'http://www.cs.waikato.ac.nz/~ml/weka/index_datasets.html'

    def download(self):
        write('Downloading.')



class Options:
    output = './slurped'
    verbose = False
    download_only = False
    force_download = False
    source = 0
    sources=[LibSVMTools.source, Weka.source]




def write(msg):
    if Options.verbose:
        print '>>> ' + msg



def usage():
    print 'Usage: ' + sys.argv[0] + ''' [options]

Options:

-o, --output
        target directory for downloads
        default: ''' + Options.output + '''

-s, --source
        source of where to slurp data from. Available sources are:
        0 - ''' + Options.sources[0] + '''
        1 - ''' + Options.sources[1] + '''
        default: ''' + str(Options.source) + '''

-v, --verbose
        enable verbose mode
        default: ''' + str(Options.verbose) + '''

-d, --download-only
        only download data, don't add to repository
        default: ''' + str(Options.download_only) + '''

-f, --force-download
        download even if file already exists
        default: ''' + str(Options.force_download) + '''

-h, --help
        show this help message and exit
'''


def parse_options():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'o:s:vdfh',
            ['output=', 'source=', 'verbose', 'download-only',
            'force-download', 'help'])
    except getopt.GetoptError, err: # print help information and exit
        print str(err) + "\n"
        usage()
        sys.exit(1)

    for o, a in opts:
        if o in ('-o', '--output'):
            Options.output = a
        elif o in ('-s', '--source'):
            a = int(a)
            if a > len(Options.sources)-1:
                usage()
                sys.exit(0)
            else:
                Options.source = a
        elif o in ('-v', '--verbose'):
            Options.verbose = True
        elif o in ('-d', '--download-only'):
            Options.download_only = True
        elif o in ('-f', '--force-download'):
            Options.force_download = True
        elif o in ('-h', '--help'):
            usage()
            sys.exit(0)
        else:
            print 'Unhandled option: ' + o
            sys.exit(2)

    if not os.path.exists(Options.output):
        write('Creating directory ' + Options.output)
        os.mkdir(Options.output)



if __name__ == '__main__':
    parse_options()

    if Options.source == 0:
        slurper = LibSVMTools()
    elif Options.source == 1:
        slurper = Weka()
    slurper.run()
    write('Done.')

    sys.exit(0)

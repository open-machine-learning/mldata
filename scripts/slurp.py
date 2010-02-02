#!/usr/bin/env python
"""
Slurp data objects from the interwebz and add them to the repository
"""

import getopt, sys, os, urllib, datetime, shutil
from HTMLParser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'mldata.settings'
from django.core.files import File
from repository.models import *
from utils import hdf5conv
from settings import MEDIA_ROOT



class LibSVMToolsHTMLParser(HTMLParser):
    def _reset(self):
        self.current = None
        self.is_name = False
        self.is_source = False
        self.is_file = False


    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.datasets = []
        self._reset()


    def handle_starttag(self, tag, attrs):
        if tag == 'h2': # new data starts here
            self.is_name = True
            self.current = {
                'name': '',
                'source': '',
                'description': '',
                'files': [],
            }
        elif tag == 'a' and self.is_file:
            self.current['files'].append(attrs[0][1])
        elif tag == 'a' and self.is_source:
            self.current['source'] += ' ' + attrs[0][1] + ' '


    def handle_endtag(self, tag):
        if tag == 'h2':
            self.is_name = False
        elif tag == 'ul' and self.current: # new data ends here
            self.current['source'] = self.current['source'].strip()
            self.current['description'] = self.current['description'].strip()
            self.datasets.append(self.current)
            self._reset()


    def handle_data(self, data):
        if self.is_name:
            self.current['name'] = data
            return

        if data.startswith('Source'):
            self.is_source = True
            return
        elif data.startswith('Files'):
            self.is_file = True
            return
        elif data.startswith('Preprocessing') or data.startswith('# '):
            self.is_source = False

        if self.current and self.is_source:
            self.current['source'] += data
        elif self.current and not self.is_file:
            self.current['description'] += data



class Slurper:
    source = None
    output = None
    format = 'hdf5'

    def fromfile(self, name):
        f = open(name, 'r')
        data = f.read()
        f.close()
        return data


    def run(self):
        progress('Slurping from ' + self.source + '.')

        self.output = Options.output + os.path.sep +\
            self.__class__.__name__ + os.path.sep
        if not os.path.exists(self.output):
            os.makedirs(self.output)

        datasets = self.collect()
        if not Options.download_only:
            self.add(datasets)


    def download(self, filename):
        src = self.source + filename
        dst = self.output + filename
        if not Options.force_download and os.path.exists(dst):
            progress(dst + ' already exists, skipping download.')
        else:
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            progress('Downloading ' + src + ' to ' + dst + '.')
            urllib.urlretrieve(src, dst)


    def parse_download(self, parser, url, type=''):
        progress('Parsing ' + url + '.')
        response = urllib.urlopen(url)
        parser.feed(''.join(response.readlines()))
        response.close()
        #parser.feed(self.fromfile('binary.html'))
        parser.close()

        for d in parser.datasets:
            d['type'] = type
            if not Options.add_only:
                for f in d['files']:
                    self.download(f)


    def collect(self):
        raise NotImplementedError('Abstract method!')


    def _create_data(self, dataset, datafile):
        progress('Creating Data item.')
        obj = Data(
            pub_date=datetime.datetime.now(),
            name=dataset['name'],
            source=dataset['source'],
            description=dataset['description'],
            version=1,
            is_public=True,
            is_current=True,
            is_approved=True,
            user_id=1,
            license_id=1,
        )
        obj.slug = obj.make_slug()
        obj.format = 'hdf5'
        obj.file = File(open(datafile))
        obj.file.name = obj.get_filename()
        obj.save()

        progress('Converting to HDF5.')
        hdf5conv.convert(datafile, self.format,
            os.path.join(MEDIA_ROOT, obj.file.name), obj.format)

        return obj


    def _create_task(self, dataset, item, num_data, num_train):
        progress('Creating Task item.')
        name = 'task_' + dataset['name']
        obj = Task(
            pub_date=datetime.datetime.now(),
            name=name,
            description=dataset['description'],
            version=1,
            is_public=True,
            is_current=True,
            user_id=1,
            license_id=1,
            tags=dataset['type'],
        )
        obj.slug = obj.make_slug()

        if dataset['type'] in ('Binary', 'MultiClass'):
            dataset['type'] = 'Classification'
        obj.type, created = TaskType.objects.get_or_create(name=dataset['type'])

        progress('Creating HDF5 split file.')
        splitfile = os.path.join(self.output, name + '.hdf5')
        indices = {'train': [range(num_data, num_data+num_train)]}
        hdf5conv.create_split(splitfile, name, indices)

        obj.splits = File(open(splitfile))
        obj.splits.name = obj.get_splitname()
        obj.save()

        # obj needs pk first for many-to-many
        obj.data.add(item)
        obj.save()

        return obj


    def _concat_datafile(self, datafile, trainfile):
        tmpfile = datafile + '.tmp'
        tmp = open(tmpfile, 'w')

        d = open(datafile,'r')
        num_data = len(d.readlines())
        d.seek(0)
        shutil.copyfileobj(d, tmp)

        t = open(trainfile,'r')
        num_train = len(t.readlines())
        t.seek(0)
        shutil.copyfileobj(t, tmp)

        d.close()
        t.close()
        tmp.close()

        return (tmpfile, num_data, num_train)


    def add(self, datasets):
        progress('Adding to repository:')
        for d in datasets:
            progress('Item ' + d['name'] + '.')
            datafile = os.path.join(self.output, d['files'][0])
            num_files = len(d['files'])
            if num_files == 1:
                self._create_data(d, datafile)
            elif num_files == 2:
                if d['files'][1].endswith('.t'):
                    tmp, num_data, num_train = self._concat_datafile(
                        datafile, os.path.join(self.output, d['files'][1]))
                    item = self._create_data(d, tmp)
                    self._create_task(d, item, num_data, num_train)
                    os.remove(tmp)
            return # return after 1st item for the time being


class LibSVMTools(Slurper):
    source = 'http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/'
    format = 'libsvm'

    def collect(self):
        datasets = []

        progress('Collecting from section binary.')
        parser = LibSVMToolsHTMLParser()
        self.parse_download(parser, self.source + 'binary.html', 'Binary')
        datasets.extend(parser.datasets)
        progress('...')
        return datasets

        progress('Collecting from section multi-class.')
        parser = LibSVMToolsHTMLParser()
        self.parse_download(parser, self.source + 'multiclass.html', 'MultiClass')
        datasets.extend(parser.datasets)
        progress('...')

        progress('Collecting from section regression.')
        parser = LibSVMToolsHTMLParser()
        self.parse_download(parser, self.source + 'regression.html', 'Regression')
        datasets.extend(parser.datasets)
        progress('...')

        progress('Collecting from section multi-label.', 'MultiLabel')
        parser = LibSVMToolsHTMLParser()
        self.parse_download(parser, self.source + 'multilabel.html')
        datasets.extend(parser.datasets)
        progress('...')

        return datasets



class Weka(Slurper):
    source = 'http://www.cs.waikato.ac.nz/~ml/weka/index_datasets.html'



class Options:
    output = './slurped'
    verbose = False
    download_only = False
    add_only = False
    force_download = False
    source = 0
    sources=[LibSVMTools.source, Weka.source]




def progress(msg):
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

-a, --add-only
        only add to repository, don't download
        default: ''' + str(Options.add_only) + '''

-f, --force-download
        download even if file already exists
        default: ''' + str(Options.force_download) + '''

-h, --help
        show this help message and exit
'''


def parse_options():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'o:s:vdafh',
            ['output=', 'source=', 'verbose', 'download-only',
            'add-only', 'force-download', 'help'])
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
        elif o in ('-a', '--add-only'):
            Options.add_only = True
        elif o in ('-f', '--force-download'):
            Options.force_download = True
        elif o in ('-h', '--help'):
            usage()
            sys.exit(0)
        else:
            print 'Unhandled option: ' + o
            sys.exit(2)

    if Options.add_only and Options.download_only:
        print 'Options add-only and download-only are mutually exclusive, please reconsider!'
        sys.exit(3)

    if not os.path.exists(Options.output):
        progress('Creating directory ' + Options.output)
        os.mkdir(Options.output)



if __name__ == '__main__':
    parse_options()

    if Options.source == 0:
        slurper = LibSVMTools()
    elif Options.source == 1:
        slurper = Weka()
    slurper.run()
    progress('Done.')

    sys.exit(0)

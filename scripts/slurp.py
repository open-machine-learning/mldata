#!/usr/bin/env python
"""
Slurp data objects from the interwebz and add them to the repository
"""

import getopt, sys, os, urllib, datetime, shutil, bz2
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


    def skippable(self, name):
        return False


    def _download(self, filename):
        src = self.source + filename
        dst = os.path.join(self.output, filename)
        if not Options.force_download and os.path.exists(dst):
            progress(dst + ' already exists, skipping download.', 3)
        else:
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            progress('Downloading ' + src + ' to ' + dst + '.', 3)
            urllib.urlretrieve(src, dst)


    def _create_data(self, parsed, datafile):
        progress('Creating Data item.', 4)
        obj = Data(
            pub_date=datetime.datetime.now(),
            name=parsed['name'],
            source=parsed['source'],
            description=parsed['description'],
            version=1,
            is_public=False,
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

        progress('Converting to HDF5.', 5)
        hdf5conv.convert(datafile, self.format,
            os.path.join(MEDIA_ROOT, obj.file.name), obj.format)

        # make it available after everythin went alright
        obj.is_public = True
        obj.save()

        return obj


    def _create_task(self, parsed, data, num_data, num_train):
        progress('Creating Task item.', 4)
        name = 'task_' + parsed['name']
        obj = Task(
            pub_date=datetime.datetime.now(),
            name=name,
            description=parsed['description'],
            version=1,
            is_public=False,
            is_current=True,
            user_id=1,
            license_id=1,
            tags=parsed['type'],
        )
        obj.slug = obj.make_slug()

        if parsed['type'] in ('Binary', 'MultiClass'):
            parsed['type'] = 'Classification'
        obj.type, created = TaskType.objects.get_or_create(name=parsed['type'])

        progress('Creating HDF5 split file.', 5)
        splitfile = os.path.join(self.output, name + '.hdf5')
        indices = {'train': [range(num_data, num_data+num_train)]}
        hdf5conv.create_split(splitfile, name, indices)

        obj.splits = File(open(splitfile))
        obj.splits.name = obj.get_splitname()
        obj.save()
        os.remove(splitfile)

        # obj needs pk first for many-to-many
        obj.data.add(data)
        obj.is_public = True
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


    def _decompress(self, oldnames):
        newnames = []
        for o in oldnames:
            o = os.path.join(self.output, o)
            n = o.replace('.bz2', '')
            if o.endswith('.bz2'):
                progress('Decompressing ' + o, 4)
                old = bz2.BZ2File(o, 'r')
                new = open(n, 'w')
                new.write(old.read())
                old.close()
                new.close()
            newnames.append(n)
        return newnames


    def _rm_decompressed(self, filenames):
        for fname in filenames:
            if fname.endswith('.bz2'):
                os.remove(os.path.join(self.output, fname.replace('.bz2', '')))


    def _add_single(self, parsed):
        self._create_data(parsed, parsed['files'][0])


    def _add_training(self, parsed):
        tmp, num_data, num_train = self._concat_datafile(
            parsed['files'][0], parsed['files'][1]
        )
        data = self._create_data(parsed, tmp)
        self._create_task(parsed, data, num_data, num_train)
        os.remove(tmp)


    def _add_scale(self, parsed):
        self._add_single(parsed)
        parsed['name'] += '_scale'
        self._add_single(parsed)


    def _add(self, parsed):
        progress('Adding to repository.', 3)
        num_files = len(parsed['files'])
        if num_files > 2:
            progress('got more files than expeced, skipping')
            return

        oldnames = parsed['files']
        parsed['files'] = self._decompress(parsed['files'])
        if num_files == 1:
            self._add_single(parsed)
        else:
            fname = parsed['files'][1]
            if fname.endswith('.t'):
                self._add_training(parsed)
            elif fname.endswith('scale'):
                self._add_scale(parsed)
            else:
                progress('unknown ending of file ' + fname)
                #raise NotImplementedError('Unknown ending of second file!')

        self._rm_decompressed(oldnames)


    def handle(self, parser, url, type=None):
        progress('Handling ' + url + '.', 1)
        response = urllib.urlopen(url)
        parser.feed(''.join(response.readlines()))
        response.close()
        #parser.feed(self.fromfile('binary.html'))
        parser.close()

        for d in parser.datasets:
            if self.skippable(d['name']):
                progress('Skipped item ' + d['name'], 2)
                continue
            else:
                progress('Item ' + d['name'], 2)

            if not Options.add_only:
                for f in d['files']:
                    self._download(f)
            if not Options.download_only:
                d['type'] = type
                self._add(d)


    def slurp(self):
        raise NotImplementedError('Abstract method!')


    def run(self):
        progress('Slurping from ' + self.source + '.')

        self.output = Options.output + os.path.sep +\
            self.__class__.__name__ + os.path.sep
        if not os.path.exists(self.output):
            os.makedirs(self.output)

        self.slurp() # implemented in child class



class LibSVMTools(Slurper):
    source = 'http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/'
    format = 'libsvm'

    def skippable(self, name):
        if name.startswith('rcv1'):
            return True
        elif name.startswith('webspam'):
            return True

        return False


    def slurp(self):
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.source + 'binary.html', 'Binary')
        return

        progress('Collecting from section multi-class.')
        parser = LibSVMToolsHTMLParser()
        self.parse_download(parser, self.source + 'multiclass.html', 'MultiClass')
        datasets.extend(parser.datasets)

        progress('Collecting from section regression.')
        parser = LibSVMToolsHTMLParser()
        self.parse_download(parser, self.source + 'regression.html', 'Regression')
        datasets.extend(parser.datasets)

        progress('Collecting from section multi-label.', 'MultiLabel')
        parser = LibSVMToolsHTMLParser()
        self.parse_download(parser, self.source + 'multilabel.html')
        datasets.extend(parser.datasets)



class Weka(Slurper):
    source = 'http://www.cs.waikato.ac.nz/~ml/weka/index_datasets.html'



class Sonnenburgs(Slurper):
    # string stuff
    source = 'http://sonnenburgs.de/media/projects/mkl_splice/'


class Options:
    output = './slurped'
    verbose = False
    download_only = False
    add_only = False
    force_download = False
    source = 0
    sources=[LibSVMTools.source, Weka.source, Sonnenburgs.source]




def progress(msg, lvl=0):
    if Options.verbose:
        print '  '*lvl + msg



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
    sys.exit(0)

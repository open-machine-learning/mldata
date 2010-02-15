#!/usr/bin/env python
"""
Slurp data objects from the interwebz and add them to the repository
"""

import getopt, sys, os, urllib, datetime, shutil, bz2, subprocess
from HTMLParser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'mldata.settings'
from django.core.files import File
from repository.models import *
from utils import hdf5conv
from settings import MEDIA_ROOT


FILESIZE_MAX = 1024*1024 # 1 MB


class SlurpHTMLParser(HTMLParser):
    def reinit(self):
        self.current = None
        self.is_name = False
        self.is_source = False
        self.is_file = False


    def init_current(self):
        self.current = {
            'name': '',
            'source': '',
            'description': '',
            'files': [],
        }


    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.datasets = []
        self.reinit()



class LibSVMToolsHTMLParser(SlurpHTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'h2': # new data starts here
            self.is_name = True
            self.init_current()
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
            self.reinit()


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



class WekaHTMLParser(SlurpHTMLParser):
    def __init__(self, *args, **kwargs):
        SlurpHTMLParser.__init__(self, *args, **kwargs)
        self.ignore = False
        self.is_description = True

    def handle_starttag(self, tag, attrs):
        if self.ignore:
            return

        if tag == 'li':
            self.init_current()
            self.is_description = True
        elif tag == 'a':
            href = None
            for a in attrs:
                if a[0] == 'href':
                    href = a[1]
            if href:
                if href.endswith('gz') or href.endswith('jar') or\
                    href.endswith('?download') or href.find('?use_mirror=') > -1:
                    self.current['files'].append(href)
                    self.current['name'] = href.split('/')[-1].split('.')[0]
                else:
                    self.current['source'] += href + ' '

    def handle_endtag(self, tag):
        if tag == 'ul': # ignore everything after first ul has ended
            self.ignore = True
            return

        if self.ignore or not self.current:
            return

        if tag == 'li':
            self.datasets.append(self.current)
            self.reinit()
        elif tag == 'a':
            self.is_description = False


    def handle_data(self, data):
        if self.ignore or not self.current:
            return

        if self.is_description:
            self.current['description'] += data



class Slurper:
    source = None
    output = None
    format = 'hdf5'

    def __init__(self, *args, **kwargs):
        self.hdf5 = hdf5conv.HDF5()


    def fromfile(self, name):
        f = open(name, 'r')
        data = f.read()
        f.close()
        return data


    def skippable(self, name):
        return False


    def get_src(self, filename):
        if filename.startswith('http://'):
            return filename
        else:
            return self.source + filename


    def get_dst(self, filename):
        if filename.startswith('http://'):
            f = filename.split('/')[-1].split('?')[0]
            return os.path.join(self.output, f)
        else:
            return os.path.join(self.output, filename)


    def _download(self, filename):
        src = self.get_src(filename)
        dst = self.get_dst(filename)
        if not Options.force_download and os.path.exists(dst):
            progress(dst + ' already exists, skipping download.', 3)
        else:
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            progress('Downloading ' + src + ' to ' + dst + '.', 3)
            urllib.urlretrieve(src, dst)


    def create_data(self, parsed, datafile):
        progress('Creating Data item ' + parsed['name'] + '.', 4)
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
            tags=parsed['type'],
        )
        obj.slug = obj.make_slug()
        obj.format = 'hdf5'
        obj.file = File(open(datafile))
        obj.file.name = obj.get_filename()
        obj.save()

        progress('Converting to HDF5.', 5)
        self.hdf5.convert(datafile, self.format,
            os.path.join(MEDIA_ROOT, obj.file.name), obj.format)

        # make it available after everythin went alright
        obj.is_public = True
        obj.save()

        return obj


    def create_task(self, parsed, data, indices={}):
        name = 'task_' + parsed['name']
        progress('Creating Task item ' + name + '.', 4)
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
            type = 'Classification'
        else:
            type = parsed['type']
        obj.type, created = TaskType.objects.get_or_create(name=type)

        progress('Creating HDF5 split file.', 5)
        splitfile = os.path.join(self.output, name + '.hdf5')
        self.hdf5.create_split(splitfile, name, indices)

        obj.splits = File(open(splitfile))
        obj.splits.name = obj.get_splitname()
        obj.save()
        os.remove(splitfile)

        # obj needs pk first for many-to-many
        obj.data.add(data)
        obj.is_public = True
        obj.save()

        return obj


    def handle(self, parser, url, type=None):
        progress('Handling ' + url + '.', 1)
        response = urllib.urlopen(url)
        parser.feed(''.join(response.readlines()))
        response.close()
        #parser.feed(self.fromfile('multilabel.html'))
        parser.close()

        for d in parser.datasets:
            if self.skippable(d['name']):
                progress('Skipped dataset ' + d['name'], 2)
                continue
            else:
                progress('Dataset ' + d['name'], 2)

            if not Options.add_only:
                for f in d['files']:
                    self._download(f)
            if not Options.download_only:
                d['type'] = type
                self.add(d)

    def decompress(self):
        raise NotImplementedError('Abstract method!')

    def rm_decompressed(self):
        raise NotImplementedError('Abstract method!')


    def slurp(self):
        raise NotImplementedError('Abstract method!')

    def add(self):
        raise NotImplementedError('Abstract method!')


    def run(self):
        progress('Slurping from ' + self.source + '.')

        self.output = os.path.join(Options.output, self.__class__.__name__)
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
        elif name.startswith('mnist8m'):
            return True

        return False


    def decompress(self, oldnames):
        newnames = []
        for o in oldnames:
            o = self.get_dst(o)
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


    def rm_decompressed(self, filenames):
        for fname in filenames:
            if fname.endswith('.bz2'):
                os.remove(os.path.join(self.output, fname.replace('.bz2', '')))


    def _concat(self, files):
        tmpfile = files[0] + '.tmp'
        tmp = open(tmpfile, 'w')
        counts = []

        for f in files:
            fh = open(f, 'r')
            shutil.copyfileobj(fh, tmp)
            fh.seek(0)
            counts.append(len(fh.readlines()))
            #counts.append(sum(1 for line in fh))
            fh.close()

        tmp.close()
        return (tmpfile, counts)


    def _add_1(self, parsed, index=0):
        self.create_data(parsed, parsed['files'][index])


    def _add_2(self, parsed, indices=(0,1)):
        fname = parsed['files'][indices[1]]
        if fname.endswith('scale'):
            self._add_1(parsed, indices[0])
            parsed['name'] += '_scale'
            self._add_1(parsed, indices[1])
        else:
            self._add_split(parsed, indices)


    def _add_3(self, parsed, indices=(0,1,2)):
        fname = parsed['files'][indices[2]]
        if fname.endswith('.r'):
            self._add_split(parsed, indices, ['validation', 'remaining'])
        elif fname.endswith('.val'):
            self._add_split(parsed, indices, ['training', 'validation'])
        elif fname.endswith('.t'): # bit of a weird case: binary splice
            self._add_split(parsed, (indices[0], indices[2]))
            parsed['name'] += '_scale'
            self._add_1(parsed, indices[1])
        elif fname.endswith('scale'): # another weird case: multiclass covtype
            self._add_1(parsed, indices[0])
            parsed['name'] += '_scale01'
            self._add_1(parsed, indices[1])
            parsed['name'] += '_scale'
            self._add_1(parsed, indices[2])
        else:
            progress('unknown ending of file ' + fname)


    def _add_4(self, parsed, indices=(0,1,2,3)):
        fname = parsed['files'][indices[3]]
        if fname.endswith('.val'):
            self._add_split(
                parsed, indices, ['testing', 'training', 'validation'])
        else:
            self._add_split(parsed, (indices[0], indices[1]))
            parsed['name'] += '_scale'
            self._add_split(parsed, (indices[2], indices[3]))


    def _add_5(self, parsed, indices=(0,1,2,3,4)):
        self._add_split(parsed, indices, ['test0', 'test1', 'test2', 'test3'])


    def _add_10(self, parsed, indices=(0,1,2,3,4,5,6,7,8,9)):
        self._add_split(
            parsed, indices, ['test1', 'test2', 'test3', 'test4', 'test5'])


    def _add_split(self, parsed, indices=(0,1), names=['testing']):
        slice = parsed['files'][indices[0]:indices[-1]+1]
        tmp, counts = self._concat(slice)
        data = self.create_data(parsed, tmp)

        split_indices = {}
        offset = len(slice) - len(names)
        prev_count = 0
        for i in xrange(offset):
            prev_count += counts[i]
        for i in xrange(len(names)):
            idx = offset + i
            split_indices[names[i]] = [
                range(prev_count, prev_count+counts[idx])
            ]
            prev_count += counts[idx]

        self.create_task(parsed, data, split_indices)
        os.remove(tmp)


    def add(self, parsed):

        for f in parsed['files']:
            if os.path.getsize(self.get_dst(f)) > FILESIZE_MAX:
                progress('Not adding, dataset too large.', 3)
                return

        progress('Adding to repository.', 3)
        oldnames = parsed['files']
        parsed['files'] = self.decompress(parsed['files'])
        num = len(parsed['files'])
        if num == 1:
            self._add_1(parsed)
        elif num == 2:
            self._add_2(parsed)
        elif num == 3:
            self._add_3(parsed)
        elif num == 4:
            self._add_4(parsed)
        elif num == 5:
            self._add_5(parsed)
        elif num == 10:
            self._add_10(parsed)

        self.rm_decompressed(oldnames)



    def slurp(self):
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.source + 'binary.html', 'Binary')
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.source + 'multiclass.html', 'MultiClass')
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.source + 'regression.html', 'Regression')
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.source + 'multilabel.html', 'MultiLabel')



class Weka(Slurper):
    source = 'http://www.cs.waikato.ac.nz/~ml/weka/index_datasets.html'

    def decompress(self, oldnames):
        newnames = []
        for o in oldnames:
            o = self.get_dst(o)
            progress('Decompressing ' + o, 4)
            ndir = os.path.join(self.output, o.split(os.sep)[-1].split('.')[0])
            if not os.path.exists(ndir):
                os.makedirs(ndir)
            cmd = 'cd ' + ndir + ' && jar -xf ' + o
            if not subprocess.call(cmd, shell=True) == 0:
                raise IOError('Unsuccessful execution of ' + cmd)
            n = o.replace('.bz2', '')
#            if o.endswith('.bz2'):
#                progress('Decompressing ' + o, 4)
#                old = bz2.BZ2File(o, 'r')
#                new = open(n, 'w')
#                new.write(old.read())
#                old.close()
#                new.close()
            newnames.append(n)
        return newnames


    def rm_decompressed(self, filenames):
        for fname in filenames:
            if fname.endswith('.bz2'):
                os.remove(os.path.join(self.output, fname.replace('.bz2', '')))


    def add(self, parsed):
        progress('Adding to repository.', 3)

        oldnames = parsed['files']
        parsed['files'] = self.decompress(parsed['files'])
        print parsed['files']
        #self.rm_decompressed(oldnames)


    def slurp(self):
        parser = WekaHTMLParser()
        self.handle(parser, self.source)


class Sonnenburgs(Slurper):
    # string stuff
    source = 'http://sonnenburgs.de/media/projects/mkl_splice/'


class Options:
    output = os.path.join(os.getcwd(), 'slurped')
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

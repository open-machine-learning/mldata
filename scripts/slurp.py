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
    """Base class for slurping HTMLParser."""

    def reinit(self):
        """Reset a few instance variables."""
        self.current = {
            'name': '',
            'source': '',
            'description': '',
            'files': [],
        }
        self.state = None


    def __init__(self, *args, **kwargs):
        """Constructor to initialise instance variables.

        @ivar datasets: collection of datasets
        @type datasets: list of dicts
        @ivar current: current dataset
        @type current: dict with fields name, source, description, files
        @ivar state: state of parser
        @type state: string
        """
        HTMLParser.__init__(self, *args, **kwargs)
        self.datasets = []
        self.reinit()


class LibSVMToolsHTMLParser(SlurpHTMLParser):
    """HTMLParser class for LibSVMTools."""

    def handle_starttag(self, tag, attrs):
        if tag == 'h2': # new data starts here
            self.state = 'name'
        elif tag == 'a' and self.state == 'file':
            self.current['files'].append(attrs[0][1])
        elif tag == 'a' and self.state == 'source':
            self.current['source'] += ' ' + attrs[0][1] + ' '


    def handle_endtag(self, tag):
        if tag == 'h2':
            self.state = None
        elif tag == 'ul' and self.state: # new data ends here
            self.current['source'] = self.current['source'].strip()
            self.current['description'] = self.current['description'].strip()
            self.datasets.append(self.current)
            self.reinit()


    def handle_data(self, data):
        if self.state == 'name':
            self.current['name'] = data
            return
        elif data.startswith('Source'):
            self.state = 'source'
            return
        elif data.startswith('Files'):
            self.state = 'file'
            return
        elif data.startswith('Preprocessing') or data.startswith('# '):
            self.state = None

        if self.state == 'source':
            self.current['source'] += data
        elif not self.state == 'file':
            self.current['description'] += data



class WekaHTMLParser(SlurpHTMLParser):
    """HTMLParser class for Weka."""

    def handle_starttag(self, tag, attrs):
        if self.state == 'done':
            return

        if tag == 'li':
            self.state = 'description'
        elif tag == 'a':
            href = None
            for a in attrs:
                if a[0] == 'href':
                    href = a[1]
                    break
            if href:
                if href.endswith('gz') or href.endswith('jar') or\
                    href.endswith('?download') or href.find('?use_mirror=') > -1:
                    self.current['files'].append(href)
                    self.current['name'] = href.split('/')[-1].split('.')[0]
                else:
                    self.current['source'] += href + ' '

    def handle_endtag(self, tag):
        if self.state == 'done':
            return

        if tag == 'ul': # ignore everything after first ul has ended
            self.state = 'done'
        elif tag == 'li':
            self.datasets.append(self.current)
            self.reinit()


    def handle_data(self, data):
        if self.state == 'done':
            return

        if self.state == 'description':
            self.current['description'] += data



class Slurper:
    """
    The slurper class to suck in data from all over the internet into
    mldata.org.

    @cvar source: source to slurp from
    @type source: string
    @cvar output: output directory for downloaded files
    @type output: string
    @cvar format: format of converted files
    @type format: string
    """
    source = None
    output = None
    format = 'hdf5'

    def __init__(self, *args, **kwargs):
        """Construct a slurper.

        @ivar hdf5: hdf5 converter object
        @type hdf5: hdf5conv.HDF5
        """
        self.hdf5 = hdf5conv.HDF5()


    def fromfile(self, name):
        f = open(name, 'r')
        data = f.read()
        f.close()
        return data


    def skippable(self, name):
        """Decide if item of given name should be skipped.

        @param name: name of item to decide on
        @type name: string
        """
        return False


    def get_src(self, filename):
        """Get source URL for given filename.

        @param filename: filename to retrieve URL for.
        @type filename: string
        """
        if filename.startswith('http://'):
            return filename
        else:
            return self.source + filename


    def get_dst(self, filename):
        """Get full local destination for given filename.

        @param filename: filename to retrieve destination for.
        @type filename: string
        """
        if filename.startswith('http://'):
            f = filename.split('/')[-1].split('?')[0]
            return os.path.join(self.output, f)
        else:
            return os.path.join(self.output, filename)


    def _download(self, filename):
        """Download helper function.

        @param filename: filename to download
        @type: string
        """
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
        """Create a repository Data object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param datafile: filename of data file (often != parsed['files'])
        @type datafile: string
        @return: a repository Data object
        @rtype: repository.Data
        """
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
        """Create a repository Task object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param data: Data object
        @type data: repository.Data
        @param indices: names of indices for split file
        @type indices: dict with fields according to split: name + index
        @return: a repository Task object
        @rtype: repository.Task
        """
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
        """Handle the given URL with given parser.

        This includes downloading + adding objects.

        @param parser: parser to use for handling the document from url
        @type parser: childclass of SlurpHTMLParser
        @param url: URL to slurp from
        @type url: string
        @param type: type of items, like regression, classification, etc.
        @type type: string
        """
        progress('Handling ' + url + '.', 1)
        response = urllib.urlopen(url)
        parser.feed(''.join(response.readlines()))
        response.close()
        parser.feed(self.fromfile('index_datasets.html'))
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

    def unzip(self):
        """Unzip downloaded files.

        @return: unzipped filenames
        @rtype: list of strings
        """
        raise NotImplementedError('Abstract method!')

    def unzip_rm(self):
        """Remove unzipped files."""
        raise NotImplementedError('Abstract method!')


    def slurp(self):
        """Commence slurping."""
        raise NotImplementedError('Abstract method!')

    def add(self):
        """Add objects from parsed document to mldata.org."""
        raise NotImplementedError('Abstract method!')


    def run(self):
        """Run the slurper - called by the class' users."""
        progress('Slurping from ' + self.source + '.')

        self.output = os.path.join(Options.output, self.__class__.__name__)
        if not os.path.exists(self.output):
            os.makedirs(self.output)

        self.slurp() # implemented in child class



class LibSVMTools(Slurper):
    """Slurp from LibSVMTools."""
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


    def unzip(self, oldnames):
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


    def unzip_rm(self, filenames):
        for fname in filenames:
            if fname.endswith('.bz2'):
                os.remove(os.path.join(self.output, fname.replace('.bz2', '')))


    def _concat(self, files):
        """Concatenate given files to one large file.

        Also counts the line numbers for each file - to be used in split
        files.

        @param files: filenames to concatenate
        @type files: list of strings
        @return: tuple with name of large file and line number counts
        """
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
        """Add one object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param index: index in parsed['files'] to use for data file
        @type index: int
        """
        self.create_data(parsed, parsed['files'][index])


    def _add_2(self, parsed, indices=(0,1)):
        """Add two objects.

        Either 1 + scaled version or 1 + split file.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param indices: indices in parsed['files'] to use for data + other file
        @type indices: tuple of ints
        """
        fname = parsed['files'][indices[1]]
        if fname.endswith('scale'):
            self._add_1(parsed, indices[0])
            parsed['name'] += '_scale'
            self._add_1(parsed, indices[1])
        else:
            self._add_split(parsed, indices)


    def _add_3(self, parsed, indices=(0,1,2)):
        """Add three objects.

        Either 1 + 2 splits, or 1 + split + scaled or 1 + 2 scaled

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param indices: indices in parsed['files'] to use for data + other file
        @type indices: tuple of ints
        """
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
        """Add four objects.

        Either 1 + 3 splits, or 1 + split + scaled + scaled split

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param indices: indices in parsed['files'] to use for data + other file
        @type indices: tuple of ints
        """
        fname = parsed['files'][indices[3]]
        if fname.endswith('.val'):
            self._add_split(
                parsed, indices, ['testing', 'training', 'validation'])
        else:
            self._add_split(parsed, (indices[0], indices[1]))
            parsed['name'] += '_scale'
            self._add_split(parsed, (indices[2], indices[3]))


    def _add_5(self, parsed, indices=(0,1,2,3,4)):
        """Add five objects, 1 + 4 splits.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param indices: indices in parsed['files'] to use for data + other file
        @type indices: tuple of ints
        """

        self._add_split(parsed, indices, ['test0', 'test1', 'test2', 'test3'])


    def _add_10(self, parsed, indices=(0,1,2,3,4,5,6,7,8,9)):
        """Add ten objects, 1 + 9 splits

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param indices: indices in parsed['files'] to use for data + other file
        @type indices: tuple of ints
        """
        self._add_split(
            parsed, indices, ['test1', 'test2', 'test3', 'test4', 'test5'])


    def _add_split(self, parsed, indices=(0,1), names=['testing']):
        """Add a split / task to mldata.org

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param indices: indices in parsed['files'] to use for data + other file
        @type indices: tuple of ints
        @param names: names of split indices
        @type names: list of strings
        """
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
        parsed['files'] = self.unzip(parsed['files'])
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

        self.unzip_rm(oldnames)



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
    """Slurp from Weka."""
    source = 'http://www.cs.waikato.ac.nz/~ml/weka/index_datasets.html'
    format = 'arff'

    def _unzip_traverse(self, dir, may_unzip=False):
        """Traverse directories to recursively unzip archives.

        @param dir: directory to look in
        @type dir: string
        @param may_unzip: if this dir may unzip files (to prevent endless loop)
        @type may_unzip: boolean
        @return: unzipped filenames
        @rtype: list of strings
        """
        items = []
        for item in os.listdir(dir):
            item = os.path.join(dir, item)
            if os.path.isdir(item):
                items.extend(self._unzip_traverse(item, True))
            elif item.endswith('.arff'):
                items.append(item)
            elif may_unzip: # assuming another archive
                items.extend(self._unzip_do(item))
        return items


    def _unzip_do(self, zip):
        """Actually perform the unzip process.

        @param zip: name of zipped file
        @type zip: string
        @return: unzipped filenames
        @rtype: list of strings
        """
        dir = os.path.join(self.output, zip.split(os.sep)[-1].split('.')[0])

        cmd = 'cd ' + dir + ' && '
        if zip.endswith('.jar'):
            cmd += 'jar -xf ' + zip
        elif zip.endswith('.bz2'):
            cmd += 'tar -xjf ' + zip
        elif zip.endswith('.gz'):
            cmd += 'tar -xzf ' + zip
        elif zip.endswith('.zip'):
            cmd += 'unzip -o -qq ' + zip
        else:
            return []

        if not os.path.exists(dir):
            os.makedirs(dir)
        if not subprocess.call(cmd, shell=True) == 0:
            raise IOError('Unsuccessful execution of ' + cmd)

        return self._unzip_traverse(dir, False)



    def unzip(self, oldnames):
        newnames = []
        for o in oldnames:
            o = self.get_dst(o)
            progress('Decompressing ' + o, 4)
            newnames.extend(self._unzip_do(o))

        return newnames


    def unzip_rm(self, fnames):
        for f in fnames:
            dir = os.path.join(self.output, f.split(os.sep)[-1].split('.')[0])
            shutil.rmtree(dir)


    def add(self, parsed):
        progress('Adding to repository.', 3)

        orig = parsed['name']
        for f in self.unzip(parsed['files']):
            splitname = ''.join(f.split(os.sep)[-1].split('.')[:-1])
            parsed['name'] = orig + ' ' + splitname
            self.create_data(parsed, f)
        self.unzip_rm(parsed['files'])


    def slurp(self):
        parser = WekaHTMLParser()
        self.handle(parser, self.source)


class Sonnenburgs(Slurper):
    """Slurp from Sonnenburgs."""
    # string stuff
    source = 'http://sonnenburgs.de/media/projects/mkl_splice/'


class Options:
    """Options to the slurper.

    Should not be instantiated.

    @cvar output: output directory of downloads
    @type output: string
    @cvar verbose: if slurper shall run in verbose mode
    @type verbose: boolean
    @cvar download_only: if slurper shall only download files, not adding
    @type download_only: boolean
    @cvar add_only: if slurper shall only add files, not downloading
    @type add_only: boolean
    @cvar force_download: force download, even if file already exists.
    @type force_download: boolean
    @cvar source: active source to slurp from
    @type soruce: int
    @cvar sources: list of available sources
    @type sources: list of strings
    """
    output = os.path.join(os.getcwd(), 'slurped')
    verbose = False
    download_only = False
    add_only = False
    force_download = False
    source = 0
    sources=[LibSVMTools.source, Weka.source, Sonnenburgs.source]




def progress(msg, lvl=0):
    """Print a progress message.

    @param msg: message to print
    @type msg: string
    @param lvl: indentation level of msg
    @type lvl: int
    """
    if Options.verbose:
        print '  '*lvl + msg



def usage():
    """Print usage of slurper."""
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
    """Parse options given to slurper."""
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

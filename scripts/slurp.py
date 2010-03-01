#!/usr/bin/env python
"""
Slurp data objects from the interwebz and add them to the repository
"""

import getopt, sys, os, urllib, datetime, shutil, bz2, subprocess, random
from HTMLParser import HTMLParser, HTMLParseError

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

    def _clean(self, fieldnames):
        """Clean the parsed fieldnames.

        @param field: the fieldnames to clean
        @type field: string
        """
        for f in fieldnames:
            # unicode conversion prevents django errors when adding to DB
            self.current[f] = unicode(self.current[f].strip(), 'latin-1')


    def reinit(self):
        """Reset a few instance variables."""
        if hasattr(self, 'current'):
            if self.current['name']:
                self._clean(['summary', 'description', 'source', 'publications'])
            if self.current['task']:
                # django url doesn't like args with slash, needs replace for tag
                self.current['tags'] = self.current['task'].replace('/', '')
            self.datasets.append(self.current)

        self.current = {
            'name': '',
            'source': '',
            'publications': '',
            'description': '',
            'summary': '',
            'task': '',
            'tags': '',
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
            self.reinit()


    def handle_data(self, data):
        if self.state == 'done':
            return

        if self.state == 'description':
            self.current['description'] += data



class UCIIndexParser(HTMLParser):
    """HTMLParser for UCI index page."""

    def __init__(self, *args, **kwargs):
        """Constructor to initialise instance variables.

        @ivar uris: collection of data URIs
        @type uris: list of strings
        """
        HTMLParser.__init__(self, *args, **kwargs)
        self.uris = []


    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for a in attrs:
                if a[0] == 'href' and a[1].startswith('datasets/'):
                    self.uris.append(a[1])
                    break



class UCIDirectoryParser(HTMLParser):
    """HTMLParser for UCI download directory page."""

    def __init__(self, *args, **kwargs):
        """Constructor to initialise instance variables.

        @ivar filenames: collection of filenames
        @type filenames: list of strings
        """
        HTMLParser.__init__(self, *args[1:], **kwargs)
        self.dir = args[0]
        self.filenames = []
        self.state = None


    def handle_starttag(self, tag, attrs):
        if tag == 'a' and self.state == 'files':
            for a in attrs:
                if a[0] == 'href' and a[1] != 'Index':
                    self.filenames.append(self.dir + a[1])

    def handle_data(self, data):
        if data == 'Parent Directory':
            self.state = 'files'



class UCIHTMLParser(SlurpHTMLParser):
    """HTMLParser class for UCI."""

    def handle_starttag(self, tag, attrs):
        if tag == 'span' and not self.state:
            for a in attrs:
                if a[0] == 'class' and a[1] == 'heading':
                    self.state = 'name'
                    break
        elif tag == 'b':
            if self.state == 'predescription':
                self.state = 'description'
            elif self.state == 'presummary':
                self.state = 'summary'
        elif tag == 'p':
            for a in attrs:
                if a[0] == 'class' and a[1] == 'small-heading':
                    if self.state == 'presource':
                        self.state = 'source'
                    elif self.state == 'source':
                        self.state = 'description'
                    break
        elif tag == 'a' and self.state == 'files':
            for a in attrs:
                if a[0] == 'href':
                    self.current['files'].append(a[1])
                    self.state = 'presummary'
                    break
        elif tag == 'a' and self.state in ('source', 'description', 'publications'):
            for a in attrs:
                if a[0] == 'href' and a[1].startswith('http://'):
                    self.current[self.state] += "\n" + a[1] + ' '
                    break



    def handle_endtag(self, tag):
        if tag == 'span' and self.state == 'name':
            self.state = 'files'
        elif tag == 'p' and self.state == 'summary':
            self.state = 'predescription'
        elif tag == 'br' and self.state == 'publications':
            self.state = 'description'
        elif tag == 'table' and self.state == 'description':
            self.state = 'presource'


    def handle_data(self, data):
        if data.startswith('Citation Request'): # end of data
            self.current['description'] =\
                self.current['description'].replace('  [View Context].', '')
            self.current['publications'] =\
                self.current['publications'].replace('  [View Context].', '').\
                    replace('[Web Link]', '')
            self.current['source'] =\
                self.current['source'].replace('Source:', '')
            self.reinit()
            return

        if self.state == 'name':
            self.current['name'] = data.replace(' Data Set', '')
        elif self.state == 'summary':
            self.current['summary'] = data[2:]
        elif self.state == 'task' and data.strip():
            self.current['task'] = data
            self.state = 'description'
        elif self.state == 'publications' and data.strip():
            self.current['publications'] += data
        elif self.state == 'description':
            if data.startswith('Associated Tasks'):
                self.state = 'task'
            elif data.startswith('Relevant Papers') or data.startswith('Papers That Cite This'):
                self.state = 'publications'
            else:
                self.current['description'] += data
        elif self.state == 'source':
            self.current['source'] += data



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

        This is a hand-selected assortment of datasets now.

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
            if self.source.endswith('/'):
                return self.source + filename
            else:
                return self.source + '/' + filename


    def get_dst(self, filename):
        """Get full local destination for given filename.

        @param filename: filename to retrieve destination for.
        @type filename: string
        """
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
            if not os.path.isdir(dst):
                progress('Downloading ' + src + ' to ' + dst + '.', 3)
                urllib.urlretrieve(src, dst)


    def _add_slug(self, obj):
        """Add a slug to given object.

        If the slug derived from the object's name already exists, it attaches
        a random number to the name and tries to add the slug anew,
        recursively if necessary.

        @param obj: object to add slug for
        @type obj: repository.Data or repository.Task
        @return: the object with slug
        @rtype: repository.Data or repository.Task
        """
        try:
            obj.slug = obj.make_slug()
        except: # wouldn't make sense to catch sqlite3.IntegrityError only
            obj.name = obj.name + '-' + str(int(random.random() * 10000))
            return self._add_slug(obj)
        return obj


    def _get_tags(self, tags):
        """Add class-constant tags to current item.

        @param tags: item-specific tags
        @type tags: string
        @return: item-specific + class-constant tags
        @rtype: string
        """
        classname = self.__class__.__name__
        # MySQL / django-tagging fix.
        if self.format.lower() != classname.lower():
            return ', '.join([tags, self.format, classname])
        else:
            return ', '.join([tags, self.format])


    def create_data(self, parsed, datafile):
        """Create a repository Data object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param datafile: filename of data file (often != parsed['files'])
        @type datafile: string
        @return: a repository Data object
        @rtype: repository.Data
        """
        obj = Data(
            pub_date=datetime.datetime.now(),
            name=parsed['name'],
            source=parsed['source'],
            description=parsed['description'],
            summary=parsed['summary'],
            publications=parsed['publications'],
            version=1,
            is_public=False,
            is_current=True,
            is_approved=True,
            user_id=1,
            license_id=1,
            tags=self._get_tags(parsed['tags']),
        )
        obj = self._add_slug(obj)
        progress('Creating Data item ' + obj.name + '.', 4)

        obj.format = 'hdf5'
        obj.file = File(open(datafile))
        obj.file.name = obj.get_filename()
        obj.save()

        progress('Converting to HDF5.', 5)
        self.hdf5.convert(datafile, self.format,
            os.path.join(MEDIA_ROOT, obj.file.name), obj.format)

        # make it available after everything went alright
        obj.is_public = True
        obj.save()

        parsed['name'] = obj.name # in case it changed due to slug
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
        obj = Task(
            pub_date=datetime.datetime.now(),
            name=name,
            description=parsed['description'],
            summary=parsed['summary'],
            publications=parsed['publications'],
            version=1,
            is_public=False,
            is_current=True,
            user_id=1,
            license_id=1,
            tags=self._get_tags(parsed['tags']),
        )
        obj = self._add_slug(obj)
        progress('Creating Task item ' + obj.name + '.', 4)

        if parsed['task'] in ('Binary', 'MultiClass'):
            ttype = 'Classification'
        else:
            ttype = parsed['task']
        obj.type, created = TaskType.objects.get_or_create(name=ttype)

        if indices:
            progress('Creating HDF5 split file.', 5)
            splitfile = os.path.join(self.output, name + '.hdf5')
            self.hdf5.create_split(splitfile, name, indices)

            obj.splits = File(open(splitfile))
            obj.splits.name = obj.get_splitname()

        obj.save()
        if indices:
            os.remove(splitfile)

        # obj needs pk first for many-to-many
        obj.data.add(data)
        obj.is_public = True
        obj.save()

        return obj


    def expand_dir(self, dirnames):
        """Expand given directory names to point to downloadable files.

        Sites like UCI don't link directly to data files, so this method
        will take care of collecting the necessary filenames from the given
        directory.

        @param dirnames: directory names to expand
        @type dirnames: list of strings
        @return: filenames in given directory
        @rtype: list of strings
        """
        return dirnames


    def handle(self, parser, url, task=None):
        """Handle the given URL with given parser.

        This includes downloading + adding objects.

        @param parser: parser to use for handling the document from url
        @type parser: childclass of SlurpHTMLParser
        @param url: URL to slurp from
        @type url: string
        @param task: task type of items, like regression, classification, etc.
        @type task: string
        """
        progress('Handling ' + url + '.', 1)
        try:
            response = urllib.urlopen(url)
            # replacement thanks to incorrect code @ UCI
            parser.feed(''.join(response.readlines()).replace('\\"', '"'))
            response.close()
            #parser.feed(self.fromfile('Iris'))
            parser.close()
        except HTMLParseError, e:
            warn('HTMLParseError: ' + str(e))
            return

        for d in parser.datasets:
            if self.skippable(d['name']):
                progress('Skipped dataset ' + d['name'], 2)
                continue
            else:
                progress('Dataset ' + d['name'], 2)

            if not Options.add_only:
                d['files'] = self.expand_dir(d['files']) # due to UCI
                for f in d['files']:
                    self._download(f)

            if not Options.download_only:
                if not d['task']:
                    d['task'] = task
                self.add(d)


    def unzip(self, oldnames):
        """Unzip downloaded files.

        @param oldnames: old filenames
        @type oldnames: list of strings
        @return: unzipped filenames
        @rtype: list of strings
        """
        return oldnames


    def unzip_rm(self, filenames):
        """Remove unzipped files.

        @param filenames: filenames to remove
        @type filenames: list of strings
        """
        return


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
        if name == 'australian':
            return False
        elif name == 'cod-rna':
            return False
        elif name == 'colon-cancer':
            return False
        elif name.startswith('duke'):
            return False
        elif name == 'ijcnn1':
            return False
        elif name == 'splice':
            return False

        elif name == 'connect-4':
            return False
        elif name == 'dna':
            return False
        elif name == 'poker':
            return False
        elif name == 'sector':
            return False

        elif name == 'yeast':
            return False
        elif name == 'mediamill':
            return False

        elif name == 'cadata':
            return False
        elif name == 'triazines':
            return False

        return True


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

    def skippable(self, name):
        if name == 'datasets-arie_ben_david':
            return False
        elif name == 'agridatasets':
            return False

        return True



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


    def get_dst(self, filename):
        f = filename.split('/')[-1].split('?')[0]
        return os.path.join(self.output, f)


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



class UCI(Slurper):
    """Slurp from UCI."""
    source = 'http://archive.ics.uci.edu/ml/datasets.html'
    format = 'uci'


    def __init__(self, *args, **kwargs):
        Slurper.__init__(self, args, kwargs)
        self.problematic = []


    def skippable(self, name):
        return False

        if name == 'Abalone':
            return False
        elif name == 'Cylinder Bands':
            return False
        elif name == 'Iris':
            return False
        elif name == 'Sponge':
            return False
        elif name == 'Zoo':
            return False

        return True


    def get_dst(self, filename):
        try:
            f = filename.split('machine-learning-databases/')[1]
        except IndexError:
            f = filename.split('databases/')[1]
        return os.path.join(self.output, f)


    def expand_dir(self, dirnames):
        filenames = []
        for d in dirnames:
            if not d.endswith('/'):
                d += '/'
            url = self.source + '/' + d
            p = UCIDirectoryParser(d)
            r = urllib.urlopen(url)
            p.feed(''.join(r.readlines()).replace('\\"', '"'))
            r.close()
            p.close()
            filenames.extend(p.filenames)
        return filenames


    def add(self, parsed):
        # only accept bla.data + bla.names for the time being...
        files = {}
        ignore_data = False
        for f in parsed['files']:
            if (f.endswith('.data') or f.endswith('-data')) and not ignore_data:
                files['data'] = f
                ignore_data = True
            elif (f.endswith('.names') or f.endswith('.info')) and 'data' in files and\
                files['data'].split('.')[:-1] == f.split('.')[:-1]:
                files['names'] = f
        if len(files) != 2:
            progress('Unknown composition of data files, skipping.', 3)
            self.problematic.append(parsed['name'])
            return

        progress('Adding to repository.', 3)
        try:
            data = self.create_data(parsed, self.get_dst(files['data']))
            if parsed['task'] != 'N/A':
                self.create_task(parsed, data)
        except ValueError:
            progress('Cannot convert this dataset.', 3)
            self.problematic.append(parsed['name'])


    def slurp(self):
        parser = UCIIndexParser()
        response = urllib.urlopen(self.source)
        parser.feed(''.join(response.readlines()).replace('\\"', '"'))
        response.close()
        #parser.feed(self.fromfile('datasets.html'))
        parser.close()
        for u in set(parser.uris):
            p = UCIHTMLParser()
            url = '/'.join(self.source.split('/')[:-1]) + '/' + u
            self.handle(p, url)
            break

        print 'Problematic datasets are:'
        for p in self.problematic:
            print p




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
    source = 2
    sources=[LibSVMTools.source, Weka.source, UCI.source, Sonnenburgs.source]




def warn(msg):
    """Print a warning message.

    @param msg: message to print
    @type msg: string
    """
    print 'WARNING: ' + msg



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
        2 - ''' + Options.sources[2] + '''
        3 - ''' + Options.sources[3] + '''
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

    slurpers = [LibSVMTools, Weka, UCI, Sonnenburgs]
    try:
        slurper = slurpers[Options.source]()
    except IndexError:
        print 'Unknown slurping source!'
        sys.exit(1)
    slurper.run()
    sys.exit(0)

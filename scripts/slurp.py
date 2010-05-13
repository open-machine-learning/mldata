#!/usr/bin/env python
"""
Slurp data objects from the interwebz and add them to the repository
"""

import getopt, sys, os, urllib, datetime, shutil, bz2, subprocess, random
import tempfile, tarfile
from HTMLParser import HTMLParser, HTMLParseError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'mldata.settings'
from django.core.files import File
from django.db import IntegrityError
from repository.models import *
from utils import h5conv
from settings import MEDIA_ROOT

MAX_SIZE_DATA = 1024 * 1024 * 512 # (512MB)


class SlurpHTMLParser(HTMLParser):
    """Base class for slurping HTMLParser."""

    def _clean(self, fieldnames):
        """Clean the parsed fieldnames.

        @param field: the fieldnames to clean
        @type field: string
        """
        for f in fieldnames:
            # unicode conversion prevents django errors when adding to DB
            if f == 'publications':
                pubs = []
                for p in self.current[f]:
                    pubs.append(unicode(p.strip(), 'latin-1'))
                self.current[f] = pubs
            else:
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
            'publications': [],
            'description': '',
            'summary': '',
            'task': '',
            'tags': '',
            'files': [],
            'license': 1,
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
            self.current['license'] = 4 # see repository/fixtures/license.json
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
            self.current['license'] = 5 # see repository/fixtures/license.json
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
    """HTMLParser class for UCI.

    @ivar pub: temporary single publication variable
    @type pub: string
    @ivar brcount: count to keep track of publication 'divisor' (== <br>)'
    @type brcount: integer
    """

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
                    link = '<a href="' + a[1] + '">' + a[1] + '</a> '
                    if self.state == 'publications':
                        self.pub += link
                    else:
                        self.current[self.state] += "\n" + link
                    break
        elif tag == 'br' and self.state == 'publications':
            if self.brcount == 0:
                self.brcount = 1
            elif self.brcount == 1:
                self.current['publications'].append(self.pub)
                self.pub = ''
                self.brcount = 0



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
            pubs = []
            for p in self.current['publications']:
                pubs.append(p.replace('  [View Context].', '').replace('[Web Link]', ''))
            self.current['publications'] = pubs
            self.current['source'] =\
                self.current['source'].replace('Source:', '')
            self.current['license'] = 6 # see repository/fixtures/license.json
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
            self.pub += data
        elif self.state == 'description':
            if data.startswith('Associated Tasks'):
                self.state = 'task'
            elif data.startswith('Relevant Papers') or data.startswith('Papers That Cite This'):
                self.state = 'publications'
                self.pub = ''
                self.brcount = 0
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
    format = 'h5'

    def __init__(self, *args, **kwargs):
        """Construct a slurper.

        @ivar hdf5: hdf5 converter object
        @type hdf5: h5conv.HDF5
        """
        self.hdf5 = h5conv.HDF5()


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
            if self.source.endswith('/'):
                return self.source + filename
            else:
                return self.source + '/' + filename


    def get_dst(self, fname):
        """Get full local destination for given filename.

        @param fname: filename to retrieve destination for.
        @type fname: string
        @return: destination filename
        @rtype: string
        """
        return os.path.join(self.output, fname)


    def get_bagofstuff(self, fnames):
        """Put given files into a big tarball.

        Usually used when file composition doesn't make sense to slurper and
        this tarball is used as Data file.

        @param fnames: names of files to put into tarball
        @type fnames: list of strings
        @return: filename of tarball
        @rtype: string
        """
        tmp, tname = tempfile.mkstemp()
        tname += '.tar.bz2'
        tarball = tarfile.open(name=tname, mode='w:bz2')
        for f in fnames:
            tarball.add(self.get_dst(f))
        tarball.close()

        return tname


    def concat(self, fnames):
        """Concatenate given files to one large file.

        @param fnames: filenames to concatenate
        @type fnames: list of strings
        @return: name of created large file
        """
        tmp, fname = tempfile.mkstemp()
        tmp = os.fdopen(tmp, 'w')
        for f in fnames:
            fh = open(f, 'r')
            shutil.copyfileobj(fh, tmp)
            fh.close()
        tmp.close()

        return fname



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
        obj.name = obj.name[:Repository._meta.get_field('name').max_length]
        obj.slug = obj.make_slug()
#        try:
#            obj.slug = obj.make_slug()
#        except IntegrityError:
#            max_num = 10000
#            rand_name = str(int(random.random() * max_num))
#            max_name = Repository._meta.get_field('name').max_length - len(str(max_num-1)) - 1
#            obj.name = obj.name[:max_name] + '-' + rand_name
#            return self._add_slug(obj)
        return obj


    def _get_tags(self, tags):
        """Add class-constant tags to current item.

        @param tags: item-specific tags
        @type tags: string
        @return: item-specific + class-constant tags
        @rtype: string
        """
        t = []
        if tags:
            t.append(tags)

        # MySQL / django-tagging fix.
        classname = self.__class__.__name__
        if self.format.lower() != classname.lower():
            t.append(classname)

        t.append(self.format)
        t.append('slurped')

        return ', '.join(t)


    def _add_publications(self, obj, publications):
        for p in publications:
            if p.startswith('<a') and p.endswith('</a>'):
                continue # skip semi-empty publication

            title = None
            try: # title finding is a bit ugly
                title = p.split('"')[1]
                if title.startswith('http://'):
                    title = None
            except IndexError:
                pass
            if not title or not title.strip():
                try:
                    title = p.split('</a>')[-1].split('.')[0]
                except IndexError:
                    pass
            if not title or len(title) < 5:
                idx = Publication._meta.get_field('title').max_length - 1
                title = p[:idx]

            pub, failed = Publication.objects.get_or_create(
                content=p, title=title.strip())
            obj.publications.add(pub)


    def create_data(self, parsed, fname):
        """Create a repository Data object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param fname: filename of data file (often != parsed['files'])
        @type fname: string
        @return: a repository Data object
        @rtype: repository.Data
        """
        if Options.convert_exist and not 'noconvert' in parsed:
            try:
                obj = Data.objects.filter(name=parsed['name'])
            except Data.DoesNotExist:
                return None
            if obj:
                self._convert_file(obj[0], fname)
            return None

        obj = Data(
            pub_date=datetime.datetime.now(),
            name=parsed['name'],
            source=parsed['source'],
            description=parsed['description'],
            summary=parsed['summary'],
            version=1,
            is_public=False,
            is_current=True,
            is_approved=True,
            user_id=1,
            license_id=parsed['license'],
            tags=self._get_tags(parsed['tags']),
        )
        try:
            obj = self._add_slug(obj)
        except IntegrityError:
            warn('Slug already exists, skipping Data item ' + obj.name + '!')
            return None
        progress('Creating Data item ' + obj.name + '.', 4)

        if 'noconvert' in parsed:
            obj.format = 'tar.bz2'
        else:
            obj.format = 'h5'
        obj.file = File(open(fname))
        obj.file.name = obj.get_filename()
        obj.save() # need to save before publications can be added
        self._add_publications(obj, parsed['publications'])
        if not 'noconvert' in parsed:
            self._convert_file(obj, fname)

        # make it available after everything went alright
        obj.is_public = True
        obj.save()

        parsed['name'] = obj.name # in case it changed due to slug
        return obj


    def create_task(self, parsed, data, fnames=[]):
        """Create a repository Task object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param data: Data object
        @type data: repository.Data
        @param fnames: filenames related to this task
        @type fnames: list of strings
        @return: a repository Task object
        @rtype: repository.Task
        """
        if not data:
            return None

        name = 'task_' + parsed['name']
        obj = Task(
            pub_date=datetime.datetime.now(),
            name=name,
            description=parsed['description'],
            summary=parsed['summary'],
            version=1,
            is_public=False,
            is_current=True,
            user_id=1,
            license_id=1,
            data=data,
            tags=self._get_tags(parsed['tags']),
        )
        try:
            obj = self._add_slug(obj)
        except IntegrityError:
            warn('Slug already exists, skipping Task item' + obj.name + '!')
            return None
        progress('Creating Task item ' + obj.name + '.', 4)

        if parsed['task'] in ('Binary', 'MultiClass'):
            ttype = 'Classification'
        else:
            ttype = parsed['task']
        obj.type, created = TaskType.objects.get_or_create(name=ttype)

        if fnames:
            progress('Creating Task file', 5)
            fname = self.hdf5.create_taskfile(name, fnames)
            obj.file = File(open(fname))
            obj.file.name = obj.get_filename() # name in $SPLITFILE_HOME

        obj.save()

        if fnames:
            os.remove(fname)

        # obj needs pk first for many-to-many
        self._add_publications(obj, parsed['publications'])
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



    def _data_exists(self, name):
        """Check if Data item with given name already exists.

        @param name: name of Data item to check
        @type name: string
        @return: if Data item already exists
        @rtype: boolean
        """
        try:
            obj = Data.objects.filter(name=name)
            return True
        except Data.DoesNotExist:
            return False

        if obj:
            return True
        else:
            return False


    def _is_too_large(self, fnames):
        """Check if datasets' files are too much for us to handle.

        @param fnames: filenames to check for size
        @type fnames: list of strings
        """
        fsize = 0
        for f in fnames:
            fsize += os.path.getsize(self.get_dst(f))
        if fsize > MAX_SIZE_DATA:
            return True
        else:
            return False


    def _convert_file(self, obj, fname):
        """Convert data file of an existing item.

        @param obj: object to convert data for
        @type obj: repository.Data
        @param fname: filename of file to convert
        @type fname: string
        @return: if conversion was successful
        @rtype: boolean
        """
        if not obj:
            return False

        converted = os.path.join(MEDIA_ROOT, obj.file.name)
        seperator = self.hdf5.infer_seperator(fname)

        progress('Converting to HDF5 (%s).' % (converted), 5)
        self.hdf5.convert(fname, self.format, converted, obj.format, seperator)
        (obj.num_instances, obj.num_attributes) =\
            self.hdf5.get_num_instattr(converted)
        obj.save()

        return True


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
            try:
                response = urllib.urlopen(url)
            except IOError, err:
                warn('IOError: ' + str(err))
                return
            # replacement thanks to incorrect code @ UCI
            parser.feed(''.join(response.readlines()).replace('\\"', '"'))
            response.close()
            #parser.feed(self.fromfile('Kinship'))
            parser.close()
        except HTMLParseError, err:
            warn('HTMLParseError: ' + str(err))
            return

        for d in parser.datasets:
            if self.skippable(d['name']):
                progress('Skipped dataset ' + d['name'], 2)
                continue
            else:
                if self._data_exists(d['name']) and not Options.convert_exist:
                    warn('Dataset ' + d['name'] + ' already exists, skipping!')
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
                if not self._is_too_large(d['files']):
                    self.add(d)
                else:
                    warn('Data %s size > %d, skipping!' % (d['name'], MAX_SIZE_DATA))



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
        return []


    def slurp(self):
        """Commence slurping."""
        raise NotImplementedError('Abstract method!')


    def add(self, parsed):
        """Add objects from parsed document to mldata.org.

        @param parsed: structure with parsed information about item
        @type parsed: dict
        """
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
        return False # allow everything now

        if name == 'australian':
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
        elif name == 'sector':
            return False

        elif name == 'yeast':
            return False
        elif name == 'scene-classification':
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
                try:
                    new.write(old.read())
                except EOFError:
                    warn("Can't decompress properly, skipping " + o)
                    continue
                finally:
                    old.close()
                    new.close()
            newnames.append(n)
        return newnames


    def unzip_rm(self, filenames):
        for fname in filenames:
            if fname.endswith('.bz2'):
                os.remove(os.path.join(self.output, fname.replace('.bz2', '')))


    def _add_1(self, parsed, fname):
        """Add one object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param fname: name of file to add
        @type fname: string
        """
        self.create_data(parsed, fname)


    def _add_2(self, parsed):
        """Add two objects.

        Either 1 + scaled version or 1 + split file.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        if parsed['files'][1].endswith('scale'):
            self._add_1(parsed, parsed['files'][0])
            parsed['name'] += '_scale'
            self._add_1(parsed, parsed['files'][1])
        else:
            self._add_datatask(parsed, parsed['files'])


    def _add_3(self, parsed):
        """Add three objects.

        Either 1 + 2 splits, or 1 + split + scaled or 1 + 2 scaled

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        fname = parsed['files'][2]
        if fname.endswith('.r') or fname.endswith('.val'):
            self._add_datatask(parsed, parsed['files'])
        elif fname.endswith('.t'): # bit of a weird case: binary splice
            self._add_datatask(parsed, [parsed['files'][0], parsed['files'][2]])
            parsed['name'] += '_scale'
            self._add_1(parsed, parsed['files'][1])
        elif fname.endswith('scale'): # another weird case: multiclass covtype
            self._add_1(parsed, parsed['files'][0])
            parsed['name'] += '_scale01'
            self._add_1(parsed, parsed['files'][1])
            parsed['name'] += '_scale'
            self._add_1(parsed, parsed['files'][2])
        else:
            progress('unknown ending of file ' + fname)


    def _add_4(self, parsed):
        """Add four objects.

        Either 1 + 3 splits, or 1 + split + scaled + scaled split

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        if parsed['files'][3].endswith('.val'):
            self._add_datatask(parsed, parsed['files'])
        else:
            self._add_datatask(parsed, parsed['files'][0:2])
            parsed['name'] += '_scale'
            self._add_datatask(parsed, parsed['files'][2:4])


    def _add_5(self, parsed):
        """Add five objects, 1 + 4 splits.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """

        self._add_datatask(parsed, parsed['files'])


    def _add_10(self, parsed):
        """Add ten objects, 1 + 9 splits

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        self._add_datatask(parsed, parsed['files'])


    def _add_datatask(self, parsed, fnames):
        """Add Data + Task to mldata.org

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param fnames: filenames of related to this task
        @type fnames: list of strings
        """
        tmp = self.concat(fnames)
        data = self.create_data(parsed, tmp)
        self.create_task(parsed, data, fnames)
        os.remove(tmp)


    def add(self, parsed):
        progress('Adding to repository.', 3)
        oldnames = parsed['files']
        parsed['files'] = self.unzip(parsed['files'])
        num = len(parsed['files'])
        if num == 1:
            self._add_1(parsed, parsed['files'][0])
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
        return False # allow everything now

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
            if self._data_exists(parsed['name']) and not Options.convert_exist:
                warn('Dataset ' + parsed['name'] + ' already exists, skipping!')
                continue
            else:
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
        return False # allow everything now

        if name == 'Abalone':
            return False
        elif name == 'Dermatology':
            return False
        elif name == 'Kinship':
            return False
        elif name == 'Sponge':
            return False
        elif name == 'Zoo':
            return False
        elif name == 'Statlog (Heart)':
            return False
        elif name == 'Gisette':
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
            try:
                r = urllib.urlopen(url)
            except IOError, err:
                warn('IOError: ' + str(err))
                return []
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
            progress('Unknown composition of data files!', 3)
            parsed['noconvert'] = True
            files['data'] = self.get_bagofstuff(parsed['files'])
            self.problematic.append(parsed['name'])
        else:
            progress('Adding to repository.', 3)
            files['data'] = self.get_dst(files['data'])
            try:
                data = self.create_data(parsed, files['data'])
                if parsed['task'] != 'N/A':
                    self.create_task(parsed, data)
            except ValueError:
                warn('Cannot convert dataset %s!' % (parsed['name']))
                self.problematic.append(parsed['name'])

        if 'noconvert' in parsed:
            os.remove(files['data'])


    def slurp(self):
        parser = UCIIndexParser()
        try:
            response = urllib.urlopen(self.source)
        except IOError, err:
            warn('IOError: ' + str(err))
            return
        parser.feed(''.join(response.readlines()).replace('\\"', '"'))
        response.close()
        #parser.feed(self.fromfile('datasets.html'))
        parser.close()

        for u in set(parser.uris):
            p = UCIHTMLParser()
            url = '/'.join(self.source.split('/')[:-1]) + '/' + u
            self.handle(p, url)

        if len(self.problematic) > 0:
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
    @cvar convert_exist: if data files of existing datasts shall be converted (implies download)
    @type convert_exist: boolean
    @cvar force_download: force download, even if file already exists.
    @type force_download: boolean
    @cvar source: active source to slurp from
    @type source: int
    @cvar sources: list of available sources
    @type sources: list of strings
    """
    output = os.path.join(os.getcwd(), 'slurped')
    verbose = False
    download_only = False
    add_only = False
    convert_exist = False
    force_download = False
    source = None
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

    for o, a in opts:
        if o in ('-o', '--output'):
            if a.startswith(os.sep): # absolute
                Options.output = a
            else: # relative
                Options.output = os.path.join(os.getcwd(), a)
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
        elif o in ('-c', '--convert-exist'):
            Options.convert_exist = True
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

    if Options.add_only and Options.convert_exist:
        print 'Options add-only and convert-exist are mutually exclusive, please reconsider!'
        sys.exit(3)

    if Options.download_only and Options.convert_exist:
        print 'Options download-only and convert-exist are mutually exclusive, please reconsider!'
        sys.exit(3)

    if not os.path.exists(Options.output):
        progress('Creating directory ' + Options.output)
        os.mkdir(Options.output)



if __name__ == '__main__':
    parse_options()

    slurpers = [LibSVMTools, Weka, UCI]
    if not Options.source in xrange(len(slurpers)):
        for s in slurpers:
            s().run()
    else:
        try:
            slurper = slurpers[Options.source]()
        except IndexError:
            print 'Unknown slurping source!'
            sys.exit(1)
        slurper.run()

    sys.exit(0)

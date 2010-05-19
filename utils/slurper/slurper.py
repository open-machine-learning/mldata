import sys, os, urllib, datetime, shutil, tempfile, tarfile
from HTMLParser import HTMLParseError

from django.core.files import File
from django.db import IntegrityError
from repository.models import Repository, Data, Task
from utils import h5conv
from settings import MEDIA_ROOT
from __init__ import MAX_SIZE_DATA


class Slurper(object):
    """
    The slurper class to suck in data from all over the internet into
    mldata.org.

    @cvar url: source URL to slurp from
    @type url: string
    @cvar output: output directory for downloaded files
    @type output: string
    @cvar format: format of converted files
    @type format: string
    """
    url = None
    output = None
    format = 'h5'

    def __init__(self, *args, **kwargs):
        """Construct a slurper.

        @ivar hdf5: hdf5 converter object
        @type hdf5: h5conv.HDF5
        @ivar options: runtime options
        @type options: __init__.Options
        """
        self.hdf5 = h5conv.HDF5()
        self.options = kwargs['options']


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
            if self.url.endswith('/'):
                return self.url + filename
            else:
                return self.url + '/' + filename


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
        if not self.options.force_download and os.path.exists(dst):
            self.progress(dst + ' already exists, skipping download.', 3)
        else:
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            if not os.path.isdir(dst):
                self.progress('Downloading ' + src + ' to ' + dst + '.', 3)
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
        if self.options.convert_exist and not 'noconvert' in parsed:
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
            self.warn('Slug already exists, skipping Data item ' + obj.name + '!')
            return None
        self.progress('Creating Data item ' + obj.name + '.', 4)

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
            self.warn('Slug already exists, skipping Task item' + obj.name + '!')
            return None
        self.progress('Creating Task item ' + obj.name + '.', 4)

        if parsed['task'] in ('Binary', 'MultiClass'):
            ttype = 'Classification'
        else:
            ttype = parsed['task']
        obj.type, created = TaskType.objects.get_or_create(name=ttype)

        if fnames:
            self.progress('Creating Task file', 5)
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
        except Data.DoesNotExist:
            return False

        if len(obj) > 0:
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

        self.progress('Converting to HDF5 (%s).' % (converted), 5)
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
        self.progress('Handling ' + url + '.', 1)
        try:
            try:
                response = urllib.urlopen(url)
            except IOError, err:
                self.warn('IOError: ' + str(err))
                return
            # replacement thanks to incorrect code @ UCI
            parser.feed(''.join(response.readlines()).replace('\\"', '"'))
            response.close()
            #parser.feed(self.fromfile('Kinship'))
            parser.close()
        except HTMLParseError, err:
            self.warn('HTMLParseError: ' + str(err))
            return

        for d in parser.datasets:
            if self.skippable(d['name']):
                self.progress('Skipped dataset ' + d['name'], 2)
                continue
            else:
                if self._data_exists(d['name']) and not self.options.convert_exist:
                    self.warn('Dataset ' + d['name'] + ' already exists, skipping!')
                    continue
                else:
                    self.progress('Dataset ' + d['name'], 2)

            if not self.options.add_only:
                d['files'] = self.expand_dir(d['files']) # due to UCI
                for f in d['files']:
                    self._download(f)

            if not self.options.download_only:
                if not d['task']:
                    d['task'] = task
                if not self._is_too_large(d['files']):
                    self.add(d)
                else:
                    self.warn('Data %s size > %d, skipping!' % (d['name'], MAX_SIZE_DATA))



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
        self.progress('Slurping from ' + self.url + '.')

        self.output = os.path.join(self.options.output, self.__class__.__name__)
        if not os.path.exists(self.output):
            os.makedirs(self.output)

        self.slurp() # implemented in child class


    def warn(self, msg):
        """Print a warning message.

        @param msg: message to print
        @type msg: string
        """
        print 'WARNING: ' + msg



    def progress(self, msg, lvl=0):
        """Print a progress message.

        @param msg: message to print
        @type msg: string
        @param lvl: indentation level of msg
        @type lvl: int
        """
        if self.options.verbose:
            print '  '*lvl + msg

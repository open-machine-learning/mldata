import sys, os, urllib, datetime, shutil, tempfile, tarfile
import ml2h5
from HTMLParser import HTMLParseError
from django.core.files import File
from django.db import IntegrityError

from repository.models import Repository, Data, Task, TaskType, Publication
from preferences.models import Preferences
from settings import MEDIA_ROOT, DATAPATH


class Slurper(object):
    """
    The slurper class to suck in data from all over the internet into
    mldata.org.

    @cvar url: source URL to slurp from
    @type url: string
    @cvar output: output directory for downloaded files
    @type output: string
    """
    url = None
    output = None

    def __init__(self, *args, **kwargs):
        """Construct a slurper.

        @ivar h5: h5 converter object
        @type h5: ml2h5.HDF5
        @ivar options: runtime options
        @type options: __init__.Options
        @ivar problematic: datasets where problems occurred
        @type problematic: list of strings
        @ivar max_data_size: max size of Data file
        @type max_data_size: integer
        """
        self.h5 = ml2h5.HDF5()
        self.options = kwargs['options']
        self.problematic = []
        self.max_data_size = Preferences.objects.get(pk=1).max_data_size


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
            fname = self.get_dst(f)
            # awkward, but fname.split(os.sep)[-2:-1] doesn't incl last
            arcname = fname.split(os.sep)
            arcname = os.sep.join([arcname[-2], arcname[-1]])
            tarball.add(fname, arcname=arcname)
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


    def _get_tags(self, parsed_tags, obj=None):
        """Add constant tags to current item.

        @param parsed_tags: item-specific, parsed tags
        @type parsed_tags: list of strings
        @param obj: object to retrieve more tag info from
        @type obj: repository.Data
        @return: item-specific + class-constant tags
        @rtype: string

        """
        tags = [p.replace('.', '-') for p in parsed_tags]
        tags.append('slurped')

        if obj:
            # MySQL / django-tagging fix.
            classname = self.__class__.__name__
            if obj.format.lower() != classname.lower():
                tags.append(classname)

            tags.append(obj.format.replace('.', '-'))

        return ', '.join(tags)


    def _get_title(self, pub):
        """Get title from publication text.

        @param pub: publication text in which to look for title
        @type pub: string
        @return: publication's title
        @rtype: string
        """
        title = None
        maxlen = Publication._meta.get_field('title').max_length
        try: # title finding is a bit ugly
            title = pub.split('"')[1][:maxlen]
            if title.startswith('http://'):
                title = None
        except IndexError:
            pass

        if not title or not title.strip():
            try:
                title = pub.split('</a>')[-1].split('.')[0][:maxlen]
            except IndexError:
                pass

        if not title or len(title) < 5:
            title = pub.strip()[:maxlen]

        return title


    def _add_publications(self, obj, publications):
        """Add given publications to given object

        @param obj: Data item to add publications to
        @type obj: repository.Data
        @param publications: publications to add
        @type publications: list of strings
        """
        for p in publications:
            if p.startswith('<a') and p.endswith('</a>'):
                continue # skip semi-empty publication

            title = self._get_title(p)
            pub, failed = Publication.objects.get_or_create(content=p, title=title)
            obj.publications.add(pub)


    def _convert_exist(self, name, fname):
        """(Re-)Convert existing Data file.

        @param name: name of Data item
        @type name: string
        @param fname: name of Data file
        @type fname: string
        @return: None
        @rtype: NoneType
        """
        try:
            obj = Data.objects.filter(name=name)
        except Data.DoesNotExist:
            return None

        if obj:
            self._handle_file(obj[0], fname)

        return None


    def create_data(self, parsed, fname):
        """Create a repository Data object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param fname: filename of data file (often != parsed['files'])
        @type fname: string
        @return: a repository Data object
        @rtype: repository.Data
        """
        if self.options.convert_exist:
            return self._convert_exist(parsed['name'], fname)

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
            format=ml2h5.fileformat.get(fname),
        )
        try:
            obj = self._add_slug(obj)
        except IntegrityError:
            self.warn('Slug already exists, skipping Data item ' + obj.name + '!')
            self.problematic.append(parsed['name'])
            return None
        self.progress('Creating Data item ' + obj.name + '.', 4)

        obj.tags = self._get_tags(parsed['tags'], obj)
        obj.save() # need to save before publications can be added
        self._add_publications(obj, parsed['publications'])
        obj = self._handle_file(obj, fname)

        # make it available after everything went alright
        obj.is_public = True
        obj.save()

        parsed['name'] = obj.name # in case it changed due to slug
        return obj


    def create_task(self, parsed, data, splitnames=[]):
        """Create a repository Task object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param data: Data object
        @type data: repository.Data
        @param splitnames: names of splitfiles related to this task
        @type splitnames: list of strings
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
            performance_measure_id=1,
            data=data,
            tags=self._get_tags(parsed['tags']),
        )
        try:
            obj = self._add_slug(obj)
        except IntegrityError:
            self.warn('Slug already exists, skipping Task item ' + name + '!')
            self.problematic.append(name)
            return None
        self.progress('Creating Task item ' + obj.name + '.', 4)

        if parsed['task'] in ('Binary', 'MultiClass'):
            ttype = 'Classification'
        else:
            ttype = parsed['task']
        obj.type, created = TaskType.objects.get_or_create(name=ttype)
        obj.save()

        if splitnames:
            fname = os.path.join(MEDIA_ROOT, obj.file.name)
            self.progress('Adding data to Task file ' + fname, 5)
            if self.h5.converter:
                labels_idx = self.h5.converter.labels_idx
            else:
                labels_idx = None
            ml2h5.task.add_data(fname, splitnames, labels_idx)

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
            fsize += os.path.getsize(f)
        if fsize > self.max_data_size:
            return True
        else:
            return False


    def _handle_file(self, obj, fname):
        """Handle data file: set format, file in object, conversion

        @param obj: object to convert data for
        @type obj: repository.Data
        @param fname: name of file to convert
        @type fname: string
        @return: if conversion was successful
        @rtype: boolean
        """
        if not obj or not fname:
            return None

        obj.file.name = os.path.join(DATAPATH, obj.get_filename())
        fname_orig = os.path.join(MEDIA_ROOT, obj.file.name)
        # keep original file for the time being
        shutil.copy(fname, fname_orig)
        if self._is_too_large([fname_orig]):
            self.warn('Size of file to convert > %d, skipping conversion!' % (self.max_data_size))
            obj.save()
            return obj

        fname_h5 = self.h5.get_filename(fname_orig)
        seperator = ml2h5.fileformat.infer_seperator(fname_orig)

        self.progress('Trying to convert to HDF5 (%s).' % (fname_h5), 5)
        try:
            verify = True
            if obj.format == 'uci':
                verify = False
            self.h5.convert(
                fname_orig, fname_h5, format_in=obj.format,
                seperator=seperator, verify=verify)
        except ml2h5.ConversionError, e:
            self.problematic.append(obj.name + ' (' + str(obj.id) + ')')
            self.progress('Error converting to HDF5: %s' % (str(e)), 6)

        if os.path.isfile(fname_h5):
            (obj.num_instances, obj.num_attributes) =\
                self.h5.get_num_instattr(fname_h5)
            # for some reason, FileField saves file.name as DATAPATH/<basename>
            obj.file.name = os.path.join(DATAPATH, fname_h5.split(os.sep)[-1])

        obj.save()
        return obj


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
                if not d['name']:
                    self.warn('Empty Dataset name!')
                    continue
                if self._data_exists(d['name']) and not self.options.convert_exist:
                    self.warn('Dataset ' + d['name'] + ' already exists, skipping!')
                    self.problematic.append(d['name'])
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
                for i in xrange(len(d['files'])): # get destination file names
                    d['files'][i] = self.get_dst(d['files'][i])
                if not self._is_too_large(d['files']):
                    self.add(d)
                else:
                    self.warn('Data %s size > %d, skipping!' % (d['name'], self.max_data_size))



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

        if len(self.problematic) > 0:
            problematic = set(self.problematic)
            self.warn('Problematic datasets are:')
            for p in self.problematic:
                self.warn(p)



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


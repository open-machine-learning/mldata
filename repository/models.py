"""
Model classes for app Repository
"""

import os, random
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

import ml2h5.task, ml2h5.data, ml2h5.converter, ml2h5.fileformat
from utils import slugify
from tagging.fields import TagField
from tagging.models import Tag, TaggedItem
from tagging.utils import calculate_cloud
from settings import DATAPATH, TASKPATH, SCOREPATH, MEDIA_ROOT



class Slug(models.Model):
    """Slug - URL-compatible item name.

    @cvar text: URL-compatible item name
    @type text: string / models.CharField
    """
    text = models.CharField(max_length=32, unique=True)

    def __unicode__(self):
        return unicode(self.text)


class License(models.Model):
    """License to be used by Data items.

    @cvar name: name of the license
    @type name: string / models.CharField
    @cvar url: url of the license
    @type url: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    def __unicode__(self):
        return unicode(self.name)



class FixedLicense(models.Model):
    """License to be used by Task or Solution items.

    For some reason, it didn't work when just inheriting, so
    the code needs to be duplicated.

    @cvar name: name of the license
    @type name: string / models.CharField
    @cvar url: url of the license
    @type url: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    def __unicode__(self):
        return unicode(self.name)



class TaskType(models.Model):
    """Type of a Task.

    @cvar name: name of the type
    @type name: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return unicode(self.name)


class TaskPerformanceMeasure(models.Model):
    """Performance measure (evaluation function) of a Task.

    @cvar name: name of the evaluation function
    @type name: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return unicode(self.name)



class Publication(models.Model):
    title = models.CharField(max_length=80)
#    slug = models.SlugField(unique=True)
    content = models.TextField()
#    firstauthor = models.CharField(max_length=256)
#    bibtype = models.CharField(max_length=256)
#    authors = models.CharField(max_length=2048)
#    year = models.IntegerField()
#    bibitem = models.TextField()
#    category = models.ForeignKey(Category)
#    abstract = models.TextField()
#    month = models.CharField(max_length=20, blank=True, null=True)
#    journal = models.CharField(max_length=256, blank=True, null=True)
#    number = models.CharField(max_length=256, blank=True, null=True)
#    institution = models.CharField(max_length=256, blank=True, null=True)
#    subcategory = models.ForeignKey('self', blank=True, null=True)
#    editor = models.CharField(max_length=2048, blank=True, null=True)
#    publisher = models.CharField(max_length=256, blank=True, null=True)
#    booktitle = models.CharField(max_length=256, blank=True, null=True)
#    pages = models.CharField(max_length=256, blank=True, null=True)
#    pdf = models.CharField(max_length=256, blank=True, null=True)
#    ps = models.CharField(max_length=256, blank=True, null=True)
#    url = models.CharField(max_length=256, blank=True, null=True)
#    note = models.CharField(max_length=256, blank=True, null=True)
#    pubtype = models.CharField(max_length=256, blank=True, null=True)
#    school = models.CharField(max_length=256, blank=True, null=True)
#    dataset = models.CharField(max_length=256, blank=True, null=True)
#    address = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return self.title



class Repository(models.Model):
    """Base class for Repository items: Data, Task, Solution

    @cvar pub_date: publication date (item creation date)
    @type pub_date: models.DateTimeField
    @cvar version: version number to flip between different incarnations of the item
    @type version: integer / models.IntegerField
    @cvar name: item's name
    @type name: string / models.CharField
    @cvar slug: item's slug
    @type slug: string / Slug
    @cvar summary: item's summary
    @type summary: string / models.CharField
    @cvar description: item's description
    @type description: string / models.TextField
    @cvar urls: URLs linking to more information about item
    @type urls: string / models.CharField
    @cvar publications: publications where item is mentioned or used
    @type publications: models.ManyToManyField
    @cvar is_public: if item is public
    @type is_public: boolean / models.BooleanField
    @cvar is_deleted: if item is deleted
    @type is_deleted: boolean / models.BooleanField
    @cvar is_current: if item is the current one
    @type is_current: boolean / models.BooleanField
    @cvar user: user who created the item
    @type user: Django User
    @cvar rating_avg: item's average overal rating
    @type rating_avg: float / models.FloatField
    @cvar rating_avg_interest: item's average interesting rating
    @type rating_avg_interest: float / models.FloatField
    @cvar rating_avg_doc: item's average documentation rating
    @type rating_avg_doc: float / models.FloatField
    @cvar rating_votes: item's total number of rating votes
    @type rating_votes: integer / models.IntegerField
    """
    pub_date = models.DateTimeField()
    version = models.IntegerField()
    name = models.CharField(max_length=32)
    slug = models.ForeignKey(Slug)
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    urls = models.CharField(max_length=255, blank=True)
    publications = models.ManyToManyField(Publication, blank=True)
    is_public = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False, editable=False)
    is_current = models.BooleanField(default=False, editable=False)
    user = models.ForeignKey(User, related_name='repository_user')
    rating_avg = models.FloatField(editable=False, default=-1)
    rating_avg_interest = models.FloatField(editable=False, default=-1)
    rating_avg_doc = models.FloatField(editable=False, default=-1)
    rating_votes = models.IntegerField(editable=False, default=0)
    downloads = models.IntegerField(editable=False, default=0)
    hits = models.IntegerField(editable=False, default=0)

    class Meta:
        """Inner meta class to specify options.

        @cvar ordering: default ordering of items in queries
        @type ordering: list
        @cvar get_latest_by: latestness will be determined by this field
        @type get_latest_by: string
        """
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'


    @classmethod
    def get_recent(klass, user):
        """Get recently changed items.

        @param user: user to get recent items for
        @type user: auth.models.user
        @return: list of recently changed items
        @rtype: list of Repository
        """
        num = 3
        qs = (Q(user__id=user.id) | Q(is_public=True)) & Q(is_current=True)

        # slices return max number of elements if num > max
        recent = list(Data.objects.filter(qs).order_by('-pub_date')[0:num])
        recent.extend(Task.objects.filter(qs).order_by('-pub_date')[0:num])
        return sorted(recent, key=lambda r: r.pub_date, reverse=True)


    @classmethod
    def get_current_tagged_items(klass, user, tag):
        """Get current items with specific tag.

        @param user: user to get current items for
        @type user: auth.models.user
        @param tag: tag to get tagged items for
        @type tag: tagging.Tag
        @return: current tagged items
        @rtype: list of Data, Task or Solution
        """
        # without if-construct sqlite3 barfs on AnonymousUser
        if user.id:
            qs = (Q(user=user) | Q(is_public=True)) & Q(is_current=True)
        else:
            qs = Q(is_public=True) & Q(is_current=True)
        if klass == Data:
            qs &= Q(is_approved=True)

        tagged = TaggedItem.objects.filter(tag=tag)
        current = klass.objects.filter(qs).order_by('name')
        items = []
        for c in current:
            for t in tagged:
                if t.object_id == c.id:
                    items.append(c)
                    break
        return items


    @classmethod
    def get_tag_cloud(klass, user):
        """Get current tags available to user.

        @param user: user to get current items for
        @type user: auth.models.user
        @return: current tags available to user
        @rtype: list of tagging.Tag
        """
        # without if-construct sqlite3 barfs on AnonymousUser
        if user.id:
            qs = (Q(user=user) | Q(is_public=True)) & Q(is_current=True)
        else:
            qs = Q(is_public=True) & Q(is_current=True)

        if klass:
            if klass == Data:
                qs = qs & Q(is_approved=True)
            tags = Tag.objects.usage_for_queryset(klass.objects.filter(qs), counts=True)
        else:
            tags = Tag.objects.usage_for_queryset(
                Data.objects.filter(qs & Q(is_approved=True)), counts=True)
            tags.extend(Tag.objects.usage_for_queryset(
                Task.objects.filter(qs), counts=True))
            tags.extend(Tag.objects.usage_for_queryset(
                Solution.objects.filter(qs), counts=True))

        current = {}
        for t in tags:
            if not t.name in current:
                current[t.name] = t
            else:
                current[t.name].count += t.count

        tags = current.values()
        if tags:
            cloud = calculate_cloud(tags, steps=2)
            random.shuffle(cloud)
        else:
            cloud = None
        return cloud



    @classmethod
    def get_object(klass, slug_or_id, version=None):
        """Retrieves an item by slug or id

        @param slug_or_id: item's slug or id for lookup
        @type slug_or_id: string or integer
        @param version: specific version of the item to retrieve
        @type version: integer
        @return: found object or None
        @rtype: Repository
        """
        if version:
            obj = klass.objects.filter(
                slug__text=slug_or_id, is_deleted=False, version=version)
        else:
            obj = klass.objects.filter(
                slug__text=slug_or_id, is_deleted=False, is_current=True)

        if obj: # by slug
            obj = obj[0]
        else: # by id
            try:
                obj = klass.objects.get(pk=slug_or_id)
            except klass.DoesNotExist:
                return None
            if not obj or obj.is_deleted:
                return None

        return obj


    @classmethod
    def set_current(klass, slug):
        """Set the latest version of the item identified by given slug to be the current one.

        @param slug: slug of item to set
        @type slug: repository.Slug
        @return: the current item or None
        @rtype: repository.Data/Task/Solution
        """
        cur = klass.objects.filter(slug=slug).\
            filter(is_deleted=False).order_by('-version')
        if not cur:
            return None
        else:
            cur = cur[0]

        prev = klass.objects.get(slug=slug, is_current=True)
        if not prev: return

        rklass = eval(klass.__name__ + 'Rating')
        try:
            rating = rklass.objects.get(user=cur.user, repository=prev)
            rating.repository = cur
            rating.save()
        except rklass.DoesNotExist:
            pass
        cur.rating_avg = prev.rating_avg
        cur.rating_avg_interest = prev.rating_avg_interest
        cur.rating_avg_doc = prev.rating_avg_doc
        cur.rating_votes = prev.rating_votes
        cur.hits = prev.hits
        cur.downloads = prev.downloads

        Comment.objects.filter(object_pk=prev.pk).update(object_pk=cur.pk)

        prev.is_current = False
        cur.is_current = True

        # this should be atomic:
        prev.save()
        cur.save()

        return cur


    @classmethod
    def search(klass, objects, searchterm):
        """Search for searchterm in objects queryset.

        @param objects: queryset to search in
        @type objects: Queryset
        @param searchterm: term to search for
        @type searchterm: string
        @return: found objects and if search failed
        @rtype: tuple of querset and boolean
        """
        # only match name and summary for now
        #Q(version__icontains=q) | Q(description__icontains=q)
        found = objects.filter(
            Q(name__icontains=searchterm) | Q(summary__icontains=searchterm)
        )

        if klass == Repository: # only approved Data items are allowed
            for f in found:
                if hasattr(f, 'data') and not f.data.is_approved:
                    found = found.exclude(id=f.id)

        if found.count() < 1:
            return objects, True
        else:
            return found, False


    def __unicode__(self):
        return unicode(self.name)


    def save(self):
        """Save item.

        Creates a slug if necessary.
        """
        if not self.slug_id:
            self.slug = self.make_slug()
        super(Repository, self).save()


    def delete(self):
        """Delete item.

        Delete the corresponding slug.
        """
        try:
            Slug.objects.get(pk=self.slug.id).delete()
        except Slug.DoesNotExist:
            pass
        # calling delete in parent not necessary
        #super(Repository, self).delete()


    def make_slug(self):
        """Make a slug generated for the item's name.

        @return: a slug
        @rtype: Slug
        @raise AttributeError: if item's name is not set
        """
        if not self.name:
            raise AttributeError, 'Attribute name is not set!'
        slug = Slug(text=slugify(self.name))
        slug.save()
        return slug


    def get_next_version(self):
        """Get next available version for this item.

        @return: next available version
        @rtype: integer
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'
        objects = self.__class__.objects.filter(
            slug=self.slug_id, is_deleted=False
        ).order_by('-version')
        return objects[0].version + 1


    def get_absolute_url(self):
        """Get absolute URL for this item, using its id.

        @return: an absolute URL
        @rtype: string
        """
        view = 'repository.views.' + self.__class__.__name__.lower() + '_view'
        return reverse(view, args=[self.id])


    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        FIXME:
        Unfortunately, it has knowledge about its derived classes which seems
        oo-unclean but is necessary for e.g. results of search function. :(

        @return: an absolute URL or None
        @rtype: string
        """
        if hasattr(self, 'solution'):
            view = 'repository.views.solution_view_slug'
            return reverse(view, args=[
                self.solution.task.data.slug.text, self.solution.task.slug.text, self.slug.text])
        elif hasattr(self, 'task'):
            view = 'repository.views.task_view_slug'
            return reverse(view, args=[self.task.data.slug.text, self.slug.text])
        else:
            view = 'repository.views.data_view_slug'
            return reverse(view, args=[self.slug.text])



    def is_owner(self, user):
        """Is given user owner of this

        @param user: user to check for
        @type user: Django User
        @return: if user owns this
        @rtype: boolean
        """
        if user.is_staff or user.is_superuser or user == self.user:
            return True
        return False


    def can_activate(self, user):
        """Can given user activate this.

        @param user: user to check for
        @type user: Django User
        @return: if user can activate this
        @rtype: boolean
        """
        if not self.is_owner(user):
            return False
        if not self.is_public:
            return True
        if not self.is_current:
            return True

        return False


    def can_delete(self, user):
        """Can given user delete this item.

        @param user: user to check for
        @type user: Django User
        @return: if user can activate this
        @rtype: boolean
        """
        ret = self.is_owner(user)
        if not ret:
            return False
        # don't delete if this is last item and something depends on it
        siblings = self.__class__.objects.filter(slug=self.slug)
        if len(siblings) == 1:
            if self.__class__ == Data:
                dependencies = Task.objects.filter(data=self)
                if len(dependencies) > 0:
                    return False
            elif self.__class__ == Task:
                dependencies = Solution.objects.filter(task=self)
                if len(dependencies) > 0:
                    return False
        return True


    def can_view(self, user):
        """Can given user view this.

        @param user: user to check for
        @type user: Django User
        @return: if user can view this
        @rtype: boolean
        """
        if self.is_public or self.is_owner(user):
            return True
        return False


    def can_download(self, user):
        """Can given user download this.

        @param user: user to check for
        @type user: Django User
        @return: if user can download this
        @rtype: boolean
        """
        return self.can_view(user)


    def can_edit(self, user):
        """Can given user edit this.

        @param user: user to check for
        @type user: Django User
        @return: if user can edit this
        @rtype: boolean
        """
        return self.can_view(user)


    def increase_downloads(self):
        """Increase hit counter for current version of given item."""
        obj = self.__class__.objects.get(slug=self.slug, is_current=True)
        obj.downloads += 1
        obj.save()


    def get_completeness(self):
        """Determine item's completeness.

        @return: completeness of item as a percentage
        @rtype: integer
        """
        if self.__class__ == Data:
            attrs = ['tags', 'description', 'license', 'summary', 'urls',
                'publications', 'source', 'measurement_details', 'usage_scenario']
        elif self.__class__ == Task:
            attrs = ['tags', 'description', 'summary', 'urls', 'publications',
                'input', 'output', 'performance_measure', 'type', 'file']
        elif self.__class__ == Solution:
            attrs = ['tags', 'description', 'summary', 'urls', 'publications',
                'feature_processing', 'parameters', 'os', 'code',
                'software_packages', 'score']
        else:
            return 0

        attrs_len = len(attrs)
        attrs_complete = 0
        for attr in attrs:
            if eval('self.' + attr):
                attrs_complete += 1
        return int((attrs_complete * 100) / attrs_len)
    completeness = property(get_completeness)


    def get_versions(self, user):
        """Retrieve all versions of this item viewable by user

        @param user: user to get versions for
        @type user: auth.model.User
        @return: viewable versions of this item
        @rtype: list of Repository
        """
        qs = Q(slug__text=self.slug.text) & Q(is_deleted=False)
        items = self.__class__.objects.filter(qs).order_by('version')
        return [i for i in items if i.can_view(user)]




    def filter_related(self, user):
        """Filter Task/Solution related to a superior Data/Task to contain only
        current and permitted Task/Solution.

        This might be part of a manager class, because it works on table-level
        for the related items. But then it works on row-level for the item
        which is looked at...

        @param user: User to filter for
        @type user: models.User
        @return: filtered items
        @rtype: list of repository.Task or repository.Solution
        """
        if self.__class__ == Data:
            qs = self.task_data
        elif self.__class__ == Task:
            qs = self.solution_set
        else:
            return None

        current = qs.filter(is_current=True)
        ret = []
        for c in current:
            if c.can_view(user):
                ret.append(c)

        return ret




class Data(Repository):
    """Repository item Data.

    @cvar source: source of the data
    @type source: string / models.CharField
    @cvar format: data format of original file, e.g. CSV, ARFF, HDF5
    @type format: string / models.CharField
    @cvar measurement_details: item's measurement details
    @type measurement_details: string / models.TextField
    @cvar usage_scenario: item's usage scenario
    @type usage_scenario: string / models.TextField
    @cvar file: data file
    @type file: models.FileField
    @cvar license: license of Data item
    @type license: License
    @cvar is_approved: is_approved is necessary for 2-step creation, don't want to call review ever again once the item is approved - review can remove permanently via 'Back' button!
    @type is_approved: boolean / models.BooleanField
    @cvar num_instances: number of instances in the Data file
    @type num_instances: integer / models.IntegerField
    @cvar num_attributes: number of attributes in the Data file
    @type num_attributes: integer / models.IntegerField
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    source = models.TextField(blank=True)
    format = models.CharField(max_length=16)
    measurement_details = models.TextField(blank=True)
    usage_scenario = models.TextField(blank=True)
    file = models.FileField(upload_to=DATAPATH)
    license = models.ForeignKey(License)
    is_approved = models.BooleanField(default=False)
    num_instances = models.IntegerField(blank=True, default=0)
    num_attributes = models.IntegerField(blank=True, default=0)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_filename(self):
        """Construct filename for Data file.

        @return: filename for Data file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return self.slug.text + '.' + self.format


    def approve(self, fname_orig, convdata):
        """Approve Data item.

        @param fname_orig: original name of Data file
        @type fname_orig: string
        @param convdata: conversion-relevant data
        @type convdata: dict of strings with keys seperator, convert, format + attribute_names_first
        @raise: ml2h5.converter.ConversionError if conversion failed
        """
        self.is_approved = True
        self.format = convdata['format']
        fname_h5 = ml2h5.fileformat.get_filename(fname_orig)

        if 'convert' in convdata and convdata['convert'] and self.format != 'h5':
            if 'attribute_names_first' in convdata and convdata['attribute_names_first']:
                anf = True
            else:
                anf = False

            verify = True
            if convdata['format'] == 'uci': verify = False

            try:
                c = ml2h5.converter.Converter(
                    fname_orig, fname_h5, format_in=self.format,
                    seperator=convdata['seperator'],
                    attribute_names_first=anf
                )
                c.run(verify=verify)
            except ml2h5.converter.ConversionError, error:
                if self.tags:
                    self.tags += ', conversion_failed'
                else:
                    self.tags = 'conversion_failed'

                self.save()
                raise ml2h5.converter.ConversionError(error.value)

        if os.path.isfile(fname_h5):
            (self.num_instances, self.num_attributes) = ml2h5.data.get_num_instattr(fname_h5)
            # keep original file for the time being
            #os.remove(fname_orig)
            # for some reason, FileField saves file.name as DATAPATH/<basename>
            self.file.name = os.path.join(DATAPATH, fname_h5.split(os.path.sep)[-1])

        self.save()





class Task(Repository):
    """Repository item Task.

    @cvar input: item's input format
    @type input: string / models.TextField
    @cvar output: item's output format
    @type output: string / models.TextField
    @cvar performance_measure: performance measure (evaluation function)
    @type performance_measure: TaskPerformanceMeasure
    @cvar performance_ordering: true => up, false => down
    @type performance_ordering: boolean / models.BooleanField
    @cvar type: item's type, e.g. Regression, Classification
    @type type: TaskType
    @cvar data: related Data item
    @type data: Data / models.ForeignKey
    @cvar data_heldback: another optional, possibly private, Data item for challenge organisers
    @type data_heldback: Data / models.ForeignKey
    @cvar file: the Task file with splits, targets, features
    @type file: models.FileField
    @cvar license: item's license
    @type license: FixedLicense
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    input = models.TextField()
    output = models.TextField()
    performance_measure = models.ForeignKey(TaskPerformanceMeasure)
    performance_ordering = models.BooleanField()
    type = models.ForeignKey(TaskType)
    data = models.ForeignKey(Data, related_name='task_data')
    data_heldback = models.ForeignKey(Data, related_name='task_data_heldback', null=True, blank=True)
    file = models.FileField(upload_to=TASKPATH)
    license = models.ForeignKey(FixedLicense, editable=False)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def predict(self, data):
        """Evaluate performance measure of given item through given data.

        @param data: uploaded result data
        @type data: string
        @return: the computed score with descriptive text
        @rtype: string
        """
        try:
            fname_task = os.path.join(MEDIA_ROOT, self.file.name)
            test_idx, output_variables = ml2h5.task.get_test_output(fname_task)
        except:
            return _("Couldn't get information from Task file!"), False

        try:
            fname_data = os.path.join(MEDIA_ROOT, self.data.file.name)
            correct = ml2h5.data.get_correct(fname_data, test_idx, output_variables)
        except:
            return _("Couldn't get correct results from Data file!"), False

        try:
            prediction = [float(d) for d in data.split("\n") if d]
        except:
            return _("Couldn't convert input data to predicted results!"), False

        len_p = len(prediction)
        len_c = len(correct)
        if len_p != len_c:
            return _("Length of correct results and submitted results doesn't match, %d != %d") % (len_c, len_p), False

        if self.performance_measure.id == 2:
            from utils.performance_measure import ClassificationErrorRate as PM
            formatstr = _('Error rate: %.2f %%')
        elif self.performance_measure.id == 3:
            from utils.performance_measure import RegressionMAE as PM
            formatstr = _('Mean Absolute Error: %f')
        elif self.performance_measure.id == 4:
            from utils.performance_measure import RegressionRMSE as PM
            formatstr = _('Root Mean Squared Error: %f')
        else:
            return _("Unknown performance measure!"), False

        score = PM().run(correct, prediction)
        return formatstr % score, True



    def get_filename(self):
        """Construct filename for Task file.

        @return: filename for Task file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return ml2h5.fileformat.get_filename(self.slug.text)


    def save(self, update_file=False, taskfile=None):
        """Save Task item, also updates Task file.

        @param update_file: if Task file should be updated on save
        @type update_file: boolean
        @param taskfile: data to write to Task file
        @type taskfile: dict with indices train_idx, test_idx, input_variables, output_variables
        """
        is_new = False
        if not self.file.name:
            self.file.name = os.path.join(TASKPATH, self.get_filename())
            is_new = True
        super(Task, self).save()

        if update_file or is_new:
            fname = os.path.join(MEDIA_ROOT, self.file.name)
            ml2h5.task.create(fname, self, taskfile)



class Solution(Repository):
    """Repository item Solution.

    @cvar feature_processing: item's feature processing
    @type feature_processing: string / models.TextField
    @cvar parameters: item's parameters
    @type parameters: string / models.CharField
    @cvar os: operating system used
    @type os: string / models.CharField
    @cvar code: computer source code to provide solution
    @type code: string / models.TextField
    @cvar software_packages: software packages needed for evaluation
    @type software_packages: string / models.TextField
    @cvar score: score file
    @type score: models.FileField
    @cvar task: related Task
    @type task: Task
    @cvar license: item's license
    @type license: FixedLicense
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    feature_processing = models.TextField(blank=True)
    parameters = models.CharField(max_length=255, blank=True)
    os = models.CharField(max_length=255, blank=True)
    code = models.TextField(blank=True)
    software_packages = models.TextField(blank=True)
    score = models.FileField(upload_to=SCOREPATH)
    task = models.ForeignKey(Task)
    license = models.ForeignKey(FixedLicense, editable=False)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_scorename(self):
        """Construct filename for score file.

        @return: filename for score file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        suffix = self.score.name.split('.')[-1]

        return self.slug.text + '.' + suffix



class Rating(models.Model):
    """Rating for a Repository item

    Each user can rate a Repository item only once, but she might change
    her rating later on.
    It acts as a base class for more specific Rating classes.

    @cvar user: rating user
    @type user: Django User
    @cvar interest: how interesting the item is
    @type interest: integer / models.IntegerField
    @cvar doc: how well the item is documented
    @type doc: integer / models.IntegerField
    """
    user = models.ForeignKey(User, related_name='rating_user')
    interest = models.IntegerField(default=0)
    doc = models.IntegerField(default=0)

    def update(self, interest, doc):
        """Update rating for an item.

        @param interest: interesting value
        @type interest: integer
        @param doc: documentation value
        @type doc: integer
        """
        self.interest = interest
        self.doc = doc
        self.save()

        repo = self.repository
        ratings = self.__class__.objects.filter(repository=repo)
        l = float(len(ratings))
        i = d = 0
        for r in ratings:
            i += r.interest
            d += r.doc

        num_scores = 2.0
        repo.rating_avg = (i + d) / (num_scores * l)
        repo.rating_avg_interest = float(i) / l
        repo.rating_avg_doc = float(d) / l
        repo.rating_votes = l
        repo.save()

    def __unicode__(self):
        try:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.repository.name))
        except AttributeError:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.id))

class DataRating(Rating):
    """Rating for a Data item."""
    repository = models.ForeignKey(Data)
class TaskRating(Rating):
    """Rating for a Task item."""
    repository = models.ForeignKey(Task)
class SolutionRating(Rating):
    """Rating for a Solution item."""
    repository = models.ForeignKey(Solution)





"""
Model classes for app Repository
"""

from django.db import models
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from utils import slugify
from tagging.fields import TagField
from settings import DATAPATH, SPLITPATH, SCOREPATH



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

    @cvar name: name of the license
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
    user = models.ForeignKey(User)
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


    def set_current(self):
        """Set this item to be the current one for this slug."""
        current = self.__class__.objects.get(slug=self.slug, is_current=True)
        if not current:
            return

        rklass = eval(self.__class__.__name__ + 'Rating')
        try:
            rating = rklass.objects.get(user=self.user, repository=current)
            rating.repository = self
            rating.save()
        except rklass.DoesNotExist:
            pass
        self.rating_avg = current.rating_avg
        self.rating_avg_interest = current.rating_avg_interest
        self.rating_avg_doc = current.rating_avg_doc
        self.rating_votes = current.rating_votes

        self.hits = current.hits
        self.downloads = current.downloads

        Comment.objects.filter(object_pk=current.pk).update(object_pk=self.pk)

        current.is_current = False
        self.is_current = True

        # this should be atomic:
        current.save()
        self.save()


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



class Data(Repository):
    """Repository item Data.

    @cvar source: source of the data
    @type source: string / models.CharField
    @cvar format: data format, e.g. CSV, ARFF, netCDF, HDF5, ODBC
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
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    source = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=16)
    measurement_details = models.TextField(blank=True)
    usage_scenario = models.TextField(blank=True)
    file = models.FileField(upload_to=DATAPATH)
    license = models.ForeignKey(License)
    is_approved = models.BooleanField(default=False)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL
        @rtype: string
        """
        view = 'repository.views.data_view_slug'
        return reverse(view, args=[self.slug.text])


    def get_filename(self):
        """Construct filename for Data file.

        @return: filename for Data file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return self.slug.text + '.' + self.format



class Task(Repository):
    """Repository item Task.

    @cvar input: item's input format
    @type input: string / models.TextField
    @cvar output: item's output format
    @type output: string / models.TextField
    @cvar performance_measure: item's performance measure
    @type performance_measure: string / models.TextField
    @cvar type: item's type, e.g. Regression, Classification
    @type type: TaskType
    @cvar data: related Data item(s)
    @type data: Data / models.ManyToManyField
    @cvar splits: item's data splits
    @type splits: models.FileField
    @cvar license: item's license
    @type license: FixedLicense
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    input = models.TextField()
    output = models.TextField()
    performance_measure = models.TextField()
    type = models.ForeignKey(TaskType)
    data = models.ManyToManyField(Data)
    splits = models.FileField(upload_to=SPLITPATH)
    license = models.ForeignKey(FixedLicense, editable=False)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL
        @rtype: string
        """
        view = 'repository.views.task_view_slug'
        return reverse(view, args=[self.data.all()[0].slug.text, self.slug.text])


    def get_splitname(self):
        """Construct filename for splits file.

        @return: filename for splits file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        suffix = self.splits.name.split('.')[-1]

        return self.slug.text + '.' + suffix



class Solution(Repository):
    """Repository item Solution.

    @cvar feature_processing: item's feature processing
    @type feature_processing: string / models.CharField
    @cvar parameters: item's parameters
    @type parameters: string / models.CharField
    @cvar os: operating system used
    @type os: string / models.CharField
    @cvar code: computer source code to provide solution
    @type code: string / models.TextField
    @cvar score: score file
    @type score: models.FileField
    @cvar task: related Task
    @type task: Task
    @cvar license: item's license
    @type license: FixedLicense
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    feature_processing = models.CharField(max_length=255, blank=True)
    parameters = models.CharField(max_length=255, blank=True)
    os = models.CharField(max_length=255, blank=True)
    code = models.TextField(blank=True)
    score = models.FileField(upload_to=SCOREPATH)
    task = models.ForeignKey(Task)
    license = models.ForeignKey(FixedLicense, editable=False)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL
        @rtype: string
        """
        view = 'repository.views.solution_view_slug'
        return reverse(view, args=[
            self.task.data.all()[0].slug.text, self.task.slug.text, self.slug.text])


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
    user = models.ForeignKey(User)
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




